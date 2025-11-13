"""
WebRTC Assistant Handler
Complete port of Go's rtc_handler/rtc_assistant.go
"""
import asyncio
import json
import os
import time
from typing import Optional, List, Dict, Any
from fastapi import WebSocket
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.sdp import candidate_from_sdp
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
import av
import numpy as np
from PIL import Image

from core.fridge import Fridge, FridgeItem
from core.recipe import RecipeSource, RecipeHelper
from core.db_handler import YoriDB
from core.object_detector import YOLODetector, ObjectDetection
from core.video_detector import VideoObjectDetector
from core.gpt_vision_detector import GPTVisionDetector
from core.realtime_assistant import GPTRealtimeAssistant
from core.openai_assistant import recommend_recipe
from models.events import YoriWebEvent
from models.cooking import Cooking
from utils.text_utils import get_random_string
from utils.audio_utils import (
    OpusHandler,
    bytes_to_int16_list,
    int16_list_to_bytes,
    resample_pcm,
    pcm16_with_single_channel,
    pcm16_with_multiple_channels,
    convert_pcm_48k_stereo_to_24k_mono
)


class AudioStreamTrack(MediaStreamTrack):
    """
    오디오 스트림 트랙 (서버 → 클라이언트)
    """
    kind = "audio"
    
    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()
    
    async def recv(self):
        """오디오 프레임 Returns"""
        audio_data = await self.queue.get()
        
        # PCM16 데이터를 AudioFrame으로 Convert
        frame = av.AudioFrame.from_ndarray(
            np.frombuffer(audio_data, dtype=np.int16).reshape(1, -1),
            format='s16',
            layout='mono'
        )
        frame.sample_rate = 24000
        frame.pts = int(time.time() * 24000)
        
        return frame
    
    async def add_audio(self, audio_data: bytes):
        """오디오 데이터 Add"""
        await self.queue.put(audio_data)


class RTCYoriAssistant:
    """
    WebRTC Yori Assistant
    Complete port of Go's RTCYoriAssistant
    """
    
    def __init__(self, websocket: WebSocket, yolo_model, api_key: str):
        """
        Args:
            websocket: FastAPI WebSocket
            yolo_model: YOLO 모델 인스턴스
            api_key: OpenAI API Key
        """
        self.websocket = websocket
        self.yolo_model = yolo_model
        self.api_key = api_key
        self.pc: Optional[RTCPeerConnection] = None
        self.pc_connected = False
        self.fridge: Optional[Fridge] = None
        self.assistant: Optional[GPTRealtimeAssistant] = None
        self.recipe_source: Optional[RecipeSource] = None
        self.recipe_helper: Optional[RecipeHelper] = None
        self.yori_db: Optional[YoriDB] = None
        self.on_cooking = False
        self.detections: List[ObjectDetection] = []
        self.detection_lock = asyncio.Lock()
        self.first_object_detected = False
        self.audio_track: Optional[AudioStreamTrack] = None
    
    async def start(self):
        """
        Assistant Start
        Complete port of Go's Start 함수
        """
        print("WebRTC Assistant connection established")
        await self._write_json({
            "type": "system",
            "event": "connected",
            "data": "websocket connected"
        })
        
        # 리소스 Initialize
        await self._init_resources()
        
        # WebRTC PeerConnection Create
        self.pc = RTCPeerConnection()
        
        # 오디오 트랙 Add (서버 → 클라이언트)
        self.audio_track = AudioStreamTrack()
        self.pc.addTrack(self.audio_track)
        
        # ICE candidate 핸들러
        @self.pc.on("icecandidate")
        async def on_ice_candidate(candidate):
            if candidate:
                await self._write_json({
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex
                })
                print("Successfully sent ICE candidate")
        
        # Connection state 변경 핸들러
        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            print(f"PeerConnection state: {self.pc.connectionState}")
            
            if self.pc.connectionState == "connected":
                print("PeerConnection has connected successfully.")
                self.pc_connected = True
                
                # GPT Assistant Initialize
                await self._init_gpt_assistant()
                
                # 오디오 전송 루프 Start
                asyncio.create_task(self._audio_sender_loop())
                
                # 이벤트 전송 루프 Start
                asyncio.create_task(self._event_sender_loop())
            
            elif self.pc.connectionState == "closed":
                print("PeerConnection closed")
                if self.assistant:
                    await self.assistant.close()
        
        # 트랙 수신 핸들러
        @self.pc.on("track")
        async def on_track(track):
            print(f"Track received: {track.kind}")
            
            if track.kind == "audio":
                await self._write_json({
                    "type": "system",
                    "event": "audio_track_received",
                    "data": "audio track received"
                })
                asyncio.create_task(self._handle_audio_track(track))
            
            elif track.kind == "video":
                await self._write_json({
                    "type": "system",
                    "event": "video_track_received",
                    "data": "video track received"
                })
                asyncio.create_task(self._handle_video_track(track))
        
        # WebSocket 메시지 루프
        await self._signaling_loop()
    
    async def _init_resources(self):
        """
        리소스 Initialize
        Go의 NewRTCYoriAssistant 로직
        """
        # 레시피 JSON 로드
        with open("./resources/recipe.json", "r", encoding="utf-8") as f:
            recipe_json = json.load(f)
        
        self.recipe_source = RecipeSource(recipe_json)
        
        # 게살 샌드위치 레시피 가져오기
        crab_sandwich_recipe = self.recipe_source.get_recipe_by_id(1)
        if not crab_sandwich_recipe:
            print("Failed to get crab sandwich recipe")
            return
        
        # DB Initialize
        mongodb_uri = os.getenv("MONGODB_URI", "")
        if mongodb_uri:
            # MongoDB 대신 SQLite 사용
            self.yori_db = YoriDB("yori.db")
            await self.yori_db.init_db()
            print("Connected to Database!")
        
        # RecipeHelper Initialize
        self.recipe_helper = RecipeHelper(crab_sandwich_recipe)
        
        # Fridge Initialize
        self.fridge = Fridge(self.recipe_source)
    
    async def _init_gpt_assistant(self):
        """
        GPT Assistant Initialize
        Complete port of Go's initGPTAssistant
        """
        if not self.api_key:
            print("API key is not provided")
            return
        
        self.assistant = GPTRealtimeAssistant(self.api_key)
        await self.assistant.connect()
        
        print("Assistant initialized")
        await self._write_json({
            "type": "system",
            "event": "assistant_initialized",
            "data": "assistant initialized"
        })
        
        # 함수 호출 핸들러 등록
        async def on_function_call(call_id: str, name: str, arguments: str) -> tuple[str, Optional[Exception]]:
            return await self._handle_function_call(call_id, name, arguments)
        
        self.assistant.on_function_call = on_function_call
    
    async def _handle_function_call(self, call_id: str, name: str, arguments: str) -> tuple[str, Optional[Exception]]:
        """
        함수 호출 핸들러 (10개 함수)
        Complete port of Go's onFunctionCall
        """
        print(f"Handling function call: {call_id}, {name}, {arguments}")
        
        try:
            if name == "get_fridge_items":
                async with self.detection_lock:
                    items = await self.fridge.get_items()
                items_json = json.dumps([item.model_dump() for item in items])
                return items_json, None
            
            elif name == "remove_fridge_item":
                args = json.loads(arguments)
                item_id = args.get("item_id")
                if not item_id:
                    return "item_id is not provided", None
                
                await self.fridge.remove(item_id)
                asyncio.create_task(self._write_json({
                    "type": "user",
                    "event": "fridge_items",
                    "data": [item.model_dump() for item in await self.fridge.get_items()]
                }))
                return "item removed", None
            
            elif name == "clear_fridge":
                await self.fridge.clear()
                asyncio.create_task(self._write_json({
                    "type": "user",
                    "event": "fridge_items",
                    "data": []
                }))
                return "fridge cleared", None
            
            elif name == "recommend_recipe":
                fridge_items = await self.fridge.get_items()
                recommendation = await recommend_recipe(
                    self.api_key,
                    fridge_items,
                    arguments
                )
                
                recipes = self.recipe_source.get_recipes_by_ids(recommendation)
                asyncio.create_task(self._write_json({
                    "type": "assistant",
                    "event": "recipe_recommend",
                    "data": [recipe.model_dump() for recipe in recipes]
                }))
                
                # DTO Create
                recipe_dtos = []
                for recipe in recipes:
                    recipe_dtos.append({
                        "id": recipe.id,
                        "name": recipe.name,
                        "description": recipe.description,
                        "ingredients": [ing.model_dump() for ing in recipe.ingredients]
                    })
                
                return json.dumps(recipe_dtos), None
            
            elif name == "select_recipe":
                args = json.loads(arguments)
                recipe_id = args.get("recipe_id")
                if recipe_id is None:
                    return "recipe_id is not provided", None
                
                if recipe_id == 1:
                    # 세션 Update
                    await self._update_session_to_start_cooking()
                    
                    asyncio.create_task(self._write_json({
                        "type": "user",
                        "event": "recipe_selected",
                        "data": {}
                    }))
                    
                    self.on_cooking = True
                    return "'게살 샌드위치'를 선택했습니다.", None
                else:
                    return "죄송합니다. 시연 모드에서는 게살 샌드위치만 가능합니다.", None
            
            elif name == "get_ready_for_cooking":
                if not self.on_cooking:
                    return "아직 요리를 Start하지 않았습니다. 레시피를 선택해주세요.", None
                return "게살 샌드위치를 선택하셨네요. 요리 준비가 complete되면 말씀해주세요!", None
            
            elif name == "go_next_step":
                if not self.on_cooking:
                    return "아직 요리를 Start하지 않았습니다. 레시피를 선택해주세요.", None
                
                step, last_step = self.recipe_helper.go_next_step()
                asyncio.create_task(self._write_json({
                    "type": "user",
                    "event": "recipe_step",
                    "data": step.model_dump()
                }))
                
                ret_message = f"{step.order}단계: {step.description}"
                if last_step:
                    ret_message += "\n마지막 단계입니다."
                
                return ret_message, None
            
            elif name == "go_previous_step":
                if not self.on_cooking:
                    return "아직 요리를 Start하지 않았습니다. 레시피를 선택해주세요.", None
                
                step = self.recipe_helper.go_previous_step()
                asyncio.create_task(self._write_json({
                    "type": "user",
                    "event": "recipe_step",
                    "data": step.model_dump()
                }))
                
                return f"{step.order}단계: {step.description}", None
            
            elif name == "recipe_done":
                if not self.on_cooking:
                    return "아직 요리를 Start하지 않았습니다. 레시피를 선택해주세요.", None
                
                done = self.recipe_helper.mark_done()
                if not done:
                    return "요리가 complete되지 않았습니다.", None
                
                self.on_cooking = False
                
                # DB에 저장
                if self.yori_db:
                    cooking = Cooking(
                        recipe_id=self.recipe_helper.get_recipe().id,
                        elapsed_seconds=int(self.recipe_helper.get_elapsed_time().total_seconds()),
                        created_at=datetime.now()
                    )
                    await self.yori_db.save_cooking(cooking)
                    
                    counts = await self.yori_db.get_cooking_counts(self.recipe_helper.get_recipe().id)
                    
                    asyncio.create_task(self._write_json({
                        "type": "user",
                        "event": "recipe_completed",
                        "data": {
                            "elapsed_time": self.recipe_helper.get_elapsed_time().total_seconds(),
                            "recipe": self.recipe_helper.get_recipe().model_dump(),
                            "counts": counts
                        }
                    }))
                    
                    return f"요리가 완성되었습니다! {self.recipe_helper.get_elapsed_time_string()}\n{counts} 번째 {self.recipe_helper.get_recipe().name} 요리입니다.", None
                
                return "요리가 완성되었습니다!", None
            
            return "no result", None
        
        except Exception as e:
            return f"error: {str(e)}", e
    
    async def _update_session_to_start_cooking(self):
        """
        세션 Update (요리 Start 모드로 전환)
        Complete port of Go's updateSessionToStartCooking
        """
        instructions = """당신은 친근한 어시스턴트입니다. 당신의 이름은 '요리보'입니다. 유저는 현재 냉장고 탐색을 끝내고, 레시피를 선택하여 요리를 Start하는 상황입니다. 유저가 요리를 준비하기까지 대기하십시오.
**next 지시문을 필수적으로 지키십시오**
- 짧고 간결하게 말하십시오. 절대로 길게 말하지 마십시오.
- 가이드는 Recipe step information와 함께 주어집니다. 가이드를 있는 그대로 말하십시오.
- 유저가 확실하게 요청하지 않는 한, Recipe step information를 건너뛰지 마십시오. 웬만하면 건너뛰지 마십시오.
- go_next_step 함수를 호출하기 전 유저에게 먼저 물어보십시오. 유저가 'e.g.' 또는 '아니오'라고 대답할 때까지 계속 되물으십시오.
- 유저의 요청이 어색하거나 식별되지 않으면, '죄송합니다. 다시 한 번 말씀해주실 수 있으신가요?'라고 되물으십시오. 유저가 명확하게 대답할 때까지 계속 되물으십시오.
- Recipe step information는 함수에 의해서만 제어됩니다. 마지막 함수에서 Returns된 Recipe step information만을 알려주십시오.
- 마지막 단계에서는 유저에게 요리를 마칠지 물어보십시오."""
        
        session_update = {
            "modalities": ["text", "audio"],
            "instructions": instructions,
            "voice": "sage",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.95,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            },
            "tools": [
                {
                    "type": "function",
                    "name": "go_next_step",
                    "description": "레시피를 next 단계로 넘어가기 위해 호출합니다. 변경된 Recipe step information를 Returns합니다. 키워드는 'next'입니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "type": "function",
                    "name": "go_previous_step",
                    "description": "레시피를 previous 단계로 돌아가기 위해 호출합니다. 변경된 Recipe step information를 Returns합니다. 키워드는 'previous'입니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "type": "function",
                    "name": "recipe_done",
                    "description": "레시피를 complete하기 위해 호출합니다. 요리 결과를 Returns합니다. 키워드는 'complete'입니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ],
            "tool_choice": "auto",
            "temperature": 0.8,
            "max_response_output_tokens": 1024
        }
        
        await self.assistant.update_session(session_update)
        await asyncio.sleep(3)
        await self.assistant.call_function("call_" + get_random_string(10), "get_ready_for_cooking", "{}")
    
    async def _audio_sender_loop(self):
        """
        오디오 전송 루프
        Go의 168-216번 라인 로직
        """
        audio_channel = await self.assistant.get_audio_response_channel()
        opus_handler = OpusHandler(48000, 2)
        
        while self.assistant and self.assistant.is_alive():
            try:
                # PCM16 오디오 수신 (24kHz, 1ch)
                audio = await audio_channel.get()
                if audio is None:
                    print("Audio channel closed, stopping audio processing")
                    break
                
                # PCM16 → Opus Convert (24kHz 1ch → 48kHz 2ch)
                opus_data = opus_handler.convert_pcm16_to_opus(audio, 24000, 1)
                
                # 전송
                for opus_packet in opus_data:
                    await self.audio_track.add_audio(opus_packet)
                
            except Exception as e:
                print(f"Audio sender loop error: {e}")
                break
    
    async def _event_sender_loop(self):
        """
        이벤트 전송 루프
        Go의 225-233번 라인 로직
        """
        event_channel = await self.assistant.get_event_channel()
        
        while self.assistant and self.assistant.is_alive():
            try:
                event = await event_channel.get()
                await self._write_json({
                    "type": event.type,
                    "event": event.event,
                    "data": event.data
                })
            except Exception as e:
                print(f"Event sender loop error: {e}")
                break
    
    async def _handle_audio_track(self, track: MediaStreamTrack):
        """
        오디오 트랙 핸들링
        Go의 handleAudioTrack (807-859번 라인)
        """
        # Assistant 대기
        try_count = 0
        while not self.assistant or not self.assistant.is_alive():
            await asyncio.sleep(0.1)
            try_count += 1
            if try_count > 100:
                print("Assistant not initialized after 10 seconds, skipping RTP track")
                return
        
        audio_buffer = bytearray()
        chunk_size = 0x8000
        
        while True:
            try:
                frame = await track.recv()
                
                # aiortc는 자동으로 Opus를 PCM으로 디코딩함
                # AudioFrame → numpy array (48kHz, 2ch)
                audio_array = frame.to_ndarray()
                
                # numpy array → bytes (int16)
                # aiortc AudioFrame format은 's16' (signed 16-bit)
                audio_bytes = audio_array.tobytes()
                
                # PCM 변환: 48kHz 2ch → 24kHz 1ch
                pcm16 = convert_pcm_48k_stereo_to_24k_mono(audio_bytes)
                
                audio_buffer.extend(pcm16)
                
                # 청크 단위로 전송
                if len(audio_buffer) >= chunk_size:
                    chunk = bytes(audio_buffer[:chunk_size])
                    audio_buffer = audio_buffer[chunk_size:]
                    
                    # first_object_detected일 때만 전송
                    if self.first_object_detected:
                        await self.assistant.send_audio(chunk)
            
            except Exception as e:
                print(f"Audio track error: {e}")
                break
    
    async def _handle_video_track(self, track: MediaStreamTrack):
        """
        비디오 트랙 핸들링
        Go의 handleVideoTrack (861-916번 라인)
        """
        # YOLO detector Create
        detector = YOLODetector(
            model_path="./resources/yori_detector.onnx",
            yaml_path="./resources/data-names.yaml",
            confidence=0.5
        )
        
        # GPT Vision detector Create (as fallback)
        gpt_detector = None
        if self.api_key:
            try:
                gpt_detector = GPTVisionDetector(self.api_key)
                print("GPT Vision fallback detector enabled")
            except Exception as e:
                print(f"Failed to create GPT Vision detector: {e}")
        
        vod = VideoObjectDetector(detector, fallback_detector=gpt_detector)
        await vod.start()
        print("Video object detector started")
        
        # 감지 결과 Handle 루프
        asyncio.create_task(self._detection_result_loop(vod))
        
        # 프레임 Handle 루프
        while True:
            try:
                frame = await track.recv()
                
                # VideoFrame → PIL Image
                img = frame.to_ndarray(format="rgb24")
                image = Image.fromarray(img)
                
                # YOLO 큐에 Add
                await vod.get_image_input_queue().put(image)
            
            except Exception as e:
                print(f"Video track error: {e}")
                await vod.stop()
                break
    
    async def _detection_result_loop(self, vod: VideoObjectDetector):
        """
        감지 결과 Handle 루프
        Go의 306-355번 라인 로직
        """
        result_queue = vod.get_detection_result_queue()
        
        while vod.is_running():
            try:
                detection_result = await result_queue.get()
                print(f"Detection length: {len(detection_result)}")
                
                async with self.detection_lock:
                    self.detections = detection_result
                    
                    # 첫 Object Detection
                    if not self.first_object_detected and len(detection_result) > 0:
                        self.first_object_detected = True
                        asyncio.create_task(self._write_json({
                            "type": "system",
                            "event": "yoribo_ready",
                            "data": "yoribo is ready"
                        }))
                
                # object_detection 이벤트 전송
                await self._write_json({
                    "type": "user",
                    "event": "object_detection",
                    "data": [d.model_dump() for d in self.detections]
                })
                
                # 냉장고 Update
                detected_items = [d.class_name for d in self.detections]
                items, changed = await self.fridge.looked(detected_items)
                
                if changed and not self.on_cooking:
                    # get_fridge_items 함수 호출
                    if self.assistant and self.assistant.is_alive():
                        asyncio.create_task(
                            self.assistant.call_function(
                                "call_" + get_random_string(10),
                                "get_fridge_items",
                                "{}"
                            )
                        )
                    
                    # fridge_items 이벤트 전송
                    await self._write_json({
                        "type": "user",
                        "event": "fridge_items",
                        "data": [item.model_dump() for item in items]
                    })
            
            except Exception as e:
                print(f"Detection result loop error: {e}")
                break
    
    async def _signaling_loop(self):
        """
        WebSocket 시그널링 루프
        Go의 367-522번 라인 로직
        """
        while True:
            try:
                msg = await self.websocket.receive_json()
                
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"Received message: {msg}")
                
                # ICE candidate Handle
                if "candidate" in msg:
                    try:
                        candidate = candidate_from_sdp(msg["candidate"])
                        candidate.sdpMid = msg.get("sdpMid")
                        candidate.sdpMLineIndex = msg.get("sdpMLineIndex")
                        await self.pc.addIceCandidate(candidate)
                    except Exception as e:
                        print(f"Failed to add ICE candidate: {e}")
                    continue
                
                msg_type = msg.get("type")
                
                if msg_type == "offer":
                    # SDP offer Handle
                    offer = RTCSessionDescription(sdp=msg["sdp"], type="offer")
                    await self.pc.setRemoteDescription(offer)
                    
                    # Answer Create
                    answer = await self.pc.createAnswer()
                    await self.pc.setLocalDescription(answer)
                    
                    # Answer 전송
                    await self._write_json({
                        "type": answer.type,
                        "sdp": answer.sdp
                    })
                
                elif msg_type == "recommend_recipe":
                    await self.assistant.call_function(
                        "call_" + get_random_string(10),
                        "recommend_recipe",
                        "{\"context\": \"유저가 '레시피 추천 버튼'을 눌렀습니다.\"}"
                    )
                
                elif msg_type == "message":
                    if self.assistant and self.assistant.is_alive():
                        await self.assistant.send_message(msg["data"])
                
                elif msg_type == "fridge":
                    data = msg.get("data")
                    if data == "items":
                        items = await self.fridge.get_items()
                        await self._write_json({
                            "type": "user",
                            "event": "fridge_items",
                            "data": [item.model_dump() for item in items]
                        })
                    elif data and data.startswith("remove_"):
                        item_id = data.split("_", 1)[1]
                        await self.fridge.remove(item_id)
                        if self.assistant and self.assistant.is_alive():
                            asyncio.create_task(
                                self.assistant.call_function(
                                    "call_" + get_random_string(10),
                                    "get_fridge_items",
                                    "{}"
                                )
                            )
                        await self._write_json({
                            "type": "user",
                            "event": "fridge_items",
                            "data": [item.model_dump() for item in await self.fridge.get_items()]
                        })
                    elif data == "clear":
                        await self.fridge.clear()
                        if self.assistant and self.assistant.is_alive():
                            asyncio.create_task(
                                self.assistant.call_function(
                                    "call_" + get_random_string(10),
                                    "get_fridge_items",
                                    "{}"
                                )
                            )
                        await self._write_json({
                            "type": "user",
                            "event": "fridge_items",
                            "data": []
                        })
                
                elif msg_type == "select_recipe":
                    recipe_id = int(msg["data"])
                    await self.assistant.call_function(
                        "call_" + get_random_string(10),
                        "select_recipe",
                        json.dumps({"recipe_id": recipe_id})
                    )
                
                elif msg_type == "recipe_cook":
                    data = msg.get("data")
                    if data == "go_next_step":
                        await self.assistant.call_function(
                            "call_" + get_random_string(10),
                            "go_next_step",
                            "{}"
                        )
                    elif data == "go_previous_step":
                        await self.assistant.call_function(
                            "call_" + get_random_string(10),
                            "go_previous_step",
                            "{}"
                        )
                    elif data == "done":
                        await self.assistant.call_function(
                            "call_" + get_random_string(10),
                            "recipe_done",
                            "{}"
                        )
                
                else:
                    print(f"Unknown message type: {msg_type}")
            
            except Exception as e:
                print(f"Signaling loop error: {e}")
                break
    
    async def _write_json(self, data: Dict[str, Any]):
        """
        WebSocket JSON 전송
        Go의 writeJSON과 동일
        """
        await self.websocket.send_json(data)
    
    async def cleanup(self):
        """리소스 정리"""
        if self.assistant:
            await self.assistant.close()
        if self.pc:
            await self.pc.close()
        if self.yori_db:
            await self.yori_db.close()


from datetime import datetime

