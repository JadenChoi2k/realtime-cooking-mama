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
from starlette.websockets import WebSocketState
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.sdp import candidate_from_sdp
import av
from av.packet import Packet
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
    convert_pcm_48k_stereo_to_24k_mono,
    convert_pcm_24k_mono_to_48k_stereo,
    OpusHandler,
)
from utils.audio_logger import AudioLogger
from fractions import Fraction


def _is_audio_debug_enabled() -> bool:
    return os.getenv("AUDIO_DEBUG", "false").lower() in ("1", "true", "yes", "on")


def _audio_debug_interval() -> int:
    if not _is_audio_debug_enabled():
        return 0
    try:
        interval = int(os.getenv("AUDIO_DEBUG_FRAME_INTERVAL", "50"))
        if interval <= 0:
            return 1
        return interval
    except ValueError:
        return 50


class OpusEncodedAudioTrack(MediaStreamTrack):
    """
    Opus로 인코딩된 패킷을 직접 반환하는 오디오 트랙
    """

    kind = "audio"

    def __init__(self):
        super().__init__()
        self.max_queue = int(os.getenv("AUDIO_OPUS_QUEUE_MAX", "200"))
        self.queue: asyncio.Queue[Packet] = asyncio.Queue()
        self.sample_rate = 48000
        self.channels = 2
        self._frames_sent = 0
        self._last_debug_log = time.time()
        self._debug_enabled = _is_audio_debug_enabled()
        self._debug_interval = _audio_debug_interval()
        if self._debug_enabled:
            print(
                f"[OpusTrack] debug enabled interval={self._debug_interval} "
                f"sample_rate={self.sample_rate} channels={self.channels}"
            )

    async def recv(self):
        packet = await self.queue.get()

        if self._debug_enabled and self._debug_interval:
            self._frames_sent += 1
            if self._frames_sent % self._debug_interval == 0:
                now = time.time()
                elapsed = now - self._last_debug_log
                queue_size = self.queue.qsize()
                print(
                    f"[OpusTrack] frames={self._frames_sent} pts={packet.pts} "
                    f"queue={queue_size} Δt={elapsed:.3f}s"
                )
                self._last_debug_log = now

        return packet

    async def add_packet(self, packet: Packet):
        if self.max_queue and self.queue.qsize() >= self.max_queue:
            try:
                _ = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            else:
                if self._debug_enabled:
                    print(
                        f"[OpusTrack] queue overflow -> dropping oldest packet (size={self.queue.qsize()})"
                    )
        await self.queue.put(packet)


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
        self.audio_track: Optional[OpusEncodedAudioTrack] = None
        self.session_id = get_random_string(12)
        audio_logging_enabled = os.getenv("AUDIO_LOGGING", "true").lower() in ("1", "true", "yes", "on")
        self.audio_logger = AudioLogger(enabled=audio_logging_enabled)
        if not self.audio_logger.is_enabled:
            print("Audio logging disabled via AUDIO_LOGGING flag")
    
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
        
        # ICE candidate 핸들러
        @self.pc.on("icecandidate")
        async def on_ice_candidate(candidate):
            if candidate:
                try:
                    await self._write_json({
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex
                    })
                    print("Successfully sent ICE candidate")
                except Exception as e:
                    print(f"Failed to send ICE candidate (websocket closed?): {e}")
        
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
                try:
                    await self._write_json({
                        "type": "system",
                        "event": "audio_track_received",
                        "data": "audio track received"
                    })
                except Exception as e:
                    print(f"Failed to notify audio track received: {e}")
                    return
                asyncio.create_task(self._handle_audio_track(track))
            
            elif track.kind == "video":
                try:
                    await self._write_json({
                        "type": "system",
                        "event": "video_track_received",
                        "data": "video track received"
                    })
                except Exception as e:
                    print(f"Failed to notify video track received: {e}")
                    return
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
            error_msg = "API key is not provided"
            print(error_msg)
            await self._write_json({
                "type": "system",
                "event": "assistant_error",
                "data": error_msg
            })
            return
        
        try:
            print(f"Initializing GPT Realtime Assistant with API key: {self.api_key[:10]}...")
            self.assistant = GPTRealtimeAssistant(self.api_key)
            await self.assistant.connect()
            
            print("Assistant initialized successfully")
            await self._write_json({
                "type": "system",
                "event": "assistant_initialized",
                "data": "assistant initialized"
            })
            
            # 함수 호출 핸들러 등록
            async def on_function_call(call_id: str, name: str, arguments: str) -> tuple[str, Optional[Exception]]:
                return await self._handle_function_call(call_id, name, arguments)
            
            self.assistant.on_function_call = on_function_call
            
        except Exception as e:
            error_msg = str(e)
            print(f"Failed to initialize assistant: {error_msg}")
            
            # 클라이언트에게 에러 메시지 전송
            await self._write_json({
                "type": "system",
                "event": "assistant_error",
                "data": error_msg
            })
            
            # assistant를 None으로 설정하여 이후 코드에서 처리
            self.assistant = None
    
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
        samples_per_frame = (self.audio_track.sample_rate // 1000) * 20  # 20ms frame at 48kHz => 960
        send_interval = samples_per_frame / self.audio_track.sample_rate
        chunk_counter = 0
        frame_counter = 0
        audio_debug = _is_audio_debug_enabled()
        diag_interval = int(os.getenv("AUDIO_SEND_METRICS_INTERVAL", "100"))
        stats = {
            "frames": 0,
            "late_frames": 0,
            "max_queue": 0,
            "total_abs_drift": 0.0,
        }
        opus_bitrate = int(os.getenv("AUDIO_OPUS_BITRATE", "64000"))
        opus_complexity = int(os.getenv("AUDIO_OPUS_COMPLEXITY", "10"))
        opus_dtx = os.getenv("AUDIO_OPUS_DTX", "false").lower() in ("1", "true", "yes", "on")
        opus_handler = OpusHandler(
            48000,
            2,
            bitrate=opus_bitrate,
            complexity=opus_complexity,
            use_dtx=opus_dtx,
        )
        if audio_debug:
            print(
                f"[AudioSenderLoop] Opus bitrate={opus_bitrate} complexity={opus_complexity} dtx={opus_dtx}"
            )
        next_pts = 0
        next_send_time = time.perf_counter()
        packet_time_base = Fraction(1, self.audio_track.sample_rate)
        self.audio_logger.ensure_wav(self.session_id, "outbound", self.audio_track.sample_rate, self.audio_track.channels)
        self.audio_logger.ensure_wav(self.session_id, "outbound_frame", self.audio_track.sample_rate, self.audio_track.channels)
        self.audio_logger.ensure_wav(self.session_id, "outbound_48k", 48000, 2)
        self.audio_logger.log_note(
            self.session_id,
            "outbound",
            "audio sender loop started; waiting for GPT audio",
            sample_rate=self.audio_track.sample_rate,
            channels=self.audio_track.channels,
        )
        
        while self.assistant and self.assistant.is_alive():
            try:
                # PCM16 오디오 수신 (24kHz, 1ch)
                try:
                    audio = await asyncio.wait_for(audio_channel.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.audio_logger.log_note(
                        self.session_id,
                        "outbound",
                        "waiting for GPT audio (no data for 5s)",
                        sample_rate=self.audio_track.sample_rate,
                        channels=self.audio_track.channels,
                    )
                    continue
                
                if audio is None:
                    print("Audio channel closed, stopping audio processing")
                    self.audio_logger.log_note(
                        self.session_id,
                        "outbound",
                        "audio channel returned None; stopping sender loop",
                        sample_rate=self.audio_track.sample_rate,
                        channels=self.audio_track.channels,
                    )
                    break
                
                # PCM -> Opus 인코딩 (Go 버전과 동일)
                chunk_counter += 1
                opus_frames = opus_handler.convert_pcm16_to_opus(audio, 24000, 1)
                self.audio_logger.log_outbound_chunk(
                    self.session_id,
                    f"pcm_{chunk_counter}",
                    audio,
                    sample_rate=24000,
                    channels=1,
                    note=f"opus_frames={len(opus_frames)}",
                )
                converted_audio = convert_pcm_24k_mono_to_48k_stereo(audio)
                self.audio_logger.log_chunk(
                    self.session_id,
                    "outbound_48k",
                    f"pcm48k_{chunk_counter}",
                    converted_audio,
                    sample_rate=48000,
                    channels=2,
                    note=f"from_chunk={chunk_counter}",
                )

                for opus_frame in opus_frames:
                    pkt = Packet(opus_frame)
                    pkt.pts = next_pts
                    pkt.time_base = packet_time_base
                    next_pts += samples_per_frame

                    now = time.perf_counter()
                    if now < next_send_time:
                        await asyncio.sleep(next_send_time - now)
                        drift = abs(time.perf_counter() - next_send_time)
                        next_send_time += send_interval
                    else:
                        drift = now - next_send_time
                        next_send_time = now + send_interval
                        stats["late_frames"] += 1
                    await self.audio_track.add_packet(pkt)
                    frame_counter += 1
                    queue_size = self.audio_track.queue.qsize()
                    self.audio_logger.log_outbound_frame(
                        self.session_id,
                        f"frame_{frame_counter}",
                        opus_frame,
                        sample_rate=self.audio_track.sample_rate,
                        channels=self.audio_track.channels,
                        note=f"pts={pkt.pts} queue_size={queue_size}",
                    )
                    stats["frames"] += 1
                    stats["total_abs_drift"] += drift
                    if queue_size > stats["max_queue"]:
                        stats["max_queue"] = queue_size
                    if diag_interval and stats["frames"] % diag_interval == 0:
                        avg_drift = stats["total_abs_drift"] / stats["frames"]
                        print(
                            f"[AudioSenderLoop][Stats] frames={stats['frames']} late={stats['late_frames']} "
                            f"avg_abs_drift={avg_drift * 1000:.2f}ms queue_max={stats['max_queue']}"
                        )
                        self.audio_logger.log_note(
                            self.session_id,
                            "outbound",
                            f"stats frames={stats['frames']} late={stats['late_frames']} "
                            f"avg_abs_drift_ms={avg_drift * 1000:.2f} queue_max={stats['max_queue']}",
                            sample_rate=self.audio_track.sample_rate,
                            channels=self.audio_track.channels,
                        )
                
            except Exception as e:
                print(f"Audio sender loop error: {e}")
                self.audio_logger.log_note(
                    self.session_id,
                    "outbound",
                    f"audio sender loop error: {e}",
                    sample_rate=self.audio_track.sample_rate,
                    channels=self.audio_track.channels,
                )
                break
        
        self.audio_logger.log_note(
            self.session_id,
            "outbound",
            "audio sender loop finished",
            sample_rate=self.audio_track.sample_rate,
            channels=self.audio_track.channels,
        )
    
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
        inbound_counter = 0
        
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
                inbound_counter += 1
                self.audio_logger.log_inbound_chunk(
                    self.session_id,
                    f"chunk_{inbound_counter}",
                    pcm16,
                    sample_rate=24000,
                    channels=1,
                    note=f"buffer_len={len(audio_buffer)}",
                )
                
                # 청크 단위로 전송
                if len(audio_buffer) >= chunk_size:
                    chunk = bytes(audio_buffer[:chunk_size])
                    audio_buffer = audio_buffer[chunk_size:]
                    
                    # 감지 여부와 상관없이 음성 전송
                    await self.assistant.send_audio(chunk)
                    self.audio_logger.log_note(
                        self.session_id,
                        "inbound",
                        f"sent_chunk size={len(chunk)} remaining_buffer={len(audio_buffer)}",
                        sample_rate=24000,
                        channels=1,
                    )
            
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
                        if candidate is None:
                            continue
                        sdp_mid = msg.get("sdpMid")
                        sdp_mline_index = msg.get("sdpMLineIndex")
                        if sdp_mid is None or sdp_mline_index is None:
                            continue
                        candidate.sdpMid = sdp_mid
                        candidate.sdpMLineIndex = sdp_mline_index
                        valid_mids = {
                            transceiver.mid
                            for transceiver in self.pc.getTransceivers()
                            if transceiver.mid is not None
                        }
                        if sdp_mid not in valid_mids:
                            print(f"Skipping ICE candidate for unknown mid {sdp_mid}")
                            continue
                        await self.pc.addIceCandidate(candidate)
                    except Exception as e:
                        print(f"Failed to add ICE candidate: {e}")
                    continue
                
                msg_type = msg.get("type")
                
                if msg_type == "offer":
                    # SDP offer Handle
                    offer = RTCSessionDescription(sdp=msg["sdp"], type="offer")
                    await self.pc.setRemoteDescription(offer)

                    if not self.audio_track:
                        self.audio_track = OpusEncodedAudioTrack()
                    audio_transceiver = None
                    for transceiver in self.pc.getTransceivers():
                        if transceiver.kind == "audio":
                            audio_transceiver = transceiver
                            break
                    if audio_transceiver:
                        try:
                            audio_transceiver.direction = "sendrecv"
                        except Exception:
                            pass
                        audio_transceiver.sender.replaceTrack(self.audio_track)
                    else:
                        audio_transceiver = self.pc.addTransceiver(self.audio_track, direction="sendrecv")
                    if _is_audio_debug_enabled():
                        sender = audio_transceiver.sender
                        try:
                            sender_info = f"sender_mid={sender.transport.mid}" if sender.transport else "sender_mid=None"
                        except Exception:
                            sender_info = "sender_mid=unknown"
                        print(
                            f"[RTC] Attached outbound audio track id={getattr(self.audio_track, 'id', 'unknown')} "
                            f"{sender_info} direction={audio_transceiver.direction}"
                        )
                    
                    # Answer Create
                    answer = await self.pc.createAnswer()
                    await self.pc.setLocalDescription(answer)
                    if _is_audio_debug_enabled():
                        self._log_local_audio_sdp(answer.sdp)
                    
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
        if not self.websocket or self.websocket.client_state != WebSocketState.CONNECTED:
            return
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            print(f"Failed to send websocket message: {e}")
    
    def _log_local_audio_sdp(self, sdp: str):
        if not sdp or not _is_audio_debug_enabled():
            return
        capture = False
        count = 0
        print("[RTC][SDP] ---- audio section start ----")
        for line in sdp.splitlines():
            if line.startswith("m=audio"):
                capture = True
            elif capture and line.startswith("m="):
                break
            if capture:
                print(f"[RTC][SDP] {line}")
                count += 1
                if count > 40:
                    print("[RTC][SDP] ... (truncated)")
                    break
        if not capture:
            print("[RTC][SDP] audio m-line not found!")
        else:
            print("[RTC][SDP] ---- audio section end ----")
    
    async def cleanup(self):
        """리소스 정리"""
        if self.assistant:
            await self.assistant.close()
        if self.pc:
            await self.pc.close()
        if self.yori_db:
            await self.yori_db.close()
        if self.audio_logger and self.session_id:
            self.audio_logger.close_session(self.session_id)
        self.audio_track = None


from datetime import datetime

