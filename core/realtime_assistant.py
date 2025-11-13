"""
OpenAI Realtime API Assistant
Go의 ybcore/realtime_assistant.go 완벽 복제
"""
import asyncio
import json
import websockets
from enum import Enum
from typing import Optional, Callable, Dict, Any
from pydantic import BaseModel
from utils.audio_utils import base64_encode_pcm16


class RealtimeAssistantStatus(Enum):
    """
    Realtime Assistant 상태
    Go의 RealtimeAssistantStatus와 동일
    """
    READY = "ready"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class RealtimeEvent(BaseModel):
    """
    Realtime 이벤트
    Go의 RealtimeEvent와 동일
    """
    type: str
    event: str
    data: str


class GPTRealtimeAssistant:
    """
    GPT Realtime Assistant
    Go의 GPTRealtimeAssistant 완벽 복제
    """
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: OpenAI API 키
        """
        self.api_key = api_key
        self.status = RealtimeAssistantStatus.READY
        self.audio_channel = asyncio.Queue()
        self.event_channel = asyncio.Queue()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.on_function_call: Optional[Callable[[str, str, str], tuple[str, Optional[Exception]]]] = None
        self.is_responding = False
        self.wait_for_sending_audio = False
        self.audio_closing = False
        self._receive_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """WebSocket 연결 및 초기화"""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.ws = await websockets.connect(url, extra_headers=headers)
        
        # 첫 메시지 수신 (session.created)
        _ = await self.ws.recv()
        
        # 수신 루프 시작
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        # 세션 초기화
        await self._init_session()
    
    async def _receive_loop(self):
        """
        메시지 수신 루프
        Go의 realtime_assistant.go 91-245번 라인 로직 완벽 복제
        """
        try:
            while True:
                msg = await self.ws.recv()
                message = json.loads(msg)
                message_type = message.get("type")
                
                # 이벤트 처리
                asyncio.create_task(self._handle_message(message_type, message))
                
        except websockets.exceptions.ConnectionClosed:
            self.status = RealtimeAssistantStatus.DISCONNECTED
        except Exception as e:
            print(f"Receive loop error: {e}")
            self.status = RealtimeAssistantStatus.ERROR
    
    async def _handle_message(self, message_type: str, message: Dict[str, Any]):
        """
        메시지 핸들링
        Go의 switch문 로직 완벽 복제
        """
        if message_type == "error":
            self.is_responding = False
            print(f"GPT Realtime API Error: {message.get('error')}")
            error_info = message.get("error", {})
            error_type = error_info.get("type")
            
            if error_type == "rate_limit_exceeded":
                self.wait_for_sending_audio = True
            elif error_type == "invalid_request_error":
                print("GPT Realtime API Invalid Request Error, skipping")
            else:
                self.status = RealtimeAssistantStatus.ERROR
        
        elif message_type == "session.created":
            self.status = RealtimeAssistantStatus.CONNECTED
        
        elif message_type == "session.updated":
            self.status = RealtimeAssistantStatus.CONNECTED
        
        elif message_type == "conversation.item.created":
            item = message.get("item", {})
            item_type = item.get("type")
            
            if item_type == "function_call_output":
                call_id = item.get("call_id")
                output = item.get("output")
                print(f"Function call output: {call_id}, {output}")
                if call_id and call_id.startswith("call_") and not self.is_responding:
                    await self._create_response()
            
            elif item_type == "function_call":
                call_id = item.get("call_id")
                name = item.get("name")
                arguments = item.get("arguments")
                if name and arguments:
                    asyncio.create_task(self._handle_function_call(call_id, name, arguments))
        
        elif message_type == "conversation.item.input_audio_transcription.completed":
            transcript = message.get("transcript", "")
            self._send_event("user", "transcript", transcript)
        
        elif message_type == "response.audio.delta":
            delta = message.get("delta", "")
            import base64
            audio = base64.b64decode(delta)
            await self._send_audio_to_channel(audio)
        
        elif message_type == "response.audio_transcript.delta":
            delta = message.get("delta", "")
            self._send_event("assistant", "transcript", delta)
        
        elif message_type == "response.audio_transcript.done":
            transcript = message.get("transcript", "")
            self._send_event("assistant", "message", transcript)
        
        elif message_type == "input_audio_buffer.speech_started":
            self._send_event("user", "speech_started", "")
        
        elif message_type == "input_audio_buffer.speech_stopped":
            self._send_event("user", "speech_stopped", "")
        
        elif message_type == "response.created":
            print("Response created")
            self.is_responding = True
            self.wait_for_sending_audio = False
            self.audio_closing = True
            
            # 오디오 채널 재생성
            old_channel = self.audio_channel
            self.audio_channel = asyncio.Queue()
            self.audio_closing = False
        
        elif message_type == "response.output_item.done":
            self.is_responding = False
            item = message.get("item", {})
            item_type = item.get("type")
            
            if item_type == "function_call":
                call_id = item.get("call_id")
                name = item.get("name")
                arguments = item.get("arguments")
                if call_id and name and arguments:
                    print(f"response.output_item.done -> function_call: {call_id}, {name}, {arguments}")
                    asyncio.create_task(self._handle_function_call(call_id, name, arguments))
        
        elif message_type == "rate_limits.updated":
            rate_limits = message.get("rate_limits", [])
            max_reset_seconds = 0.0
            for limit in rate_limits:
                reset_seconds = limit.get("reset_seconds", 0)
                if reset_seconds > max_reset_seconds:
                    max_reset_seconds = reset_seconds
            
            print(f"Maximum reset_seconds: {max_reset_seconds}")
            
            async def reset_wait_flag():
                await asyncio.sleep(max_reset_seconds)
                self.wait_for_sending_audio = False
            
            asyncio.create_task(reset_wait_flag())
    
    async def _init_session(self):
        """
        세션 초기화
        Go의 sessionUpdate와 동일
        """
        instructions = """당신은 친근한 어시스턴트입니다. 당신의 이름은 '요리보'입니다. 인사와 함께 유저를 반겨줍니다.
**다음 지시문을 필수적으로 지켜야 합니다.**
- 짧고 간결하게 말하십시오. 절대로 길게 말하지 마십시오.
- 같은 말을 반복하지 마십시오.
- 당신은 사용자의 냉장고 식재료를 스캔하여, 사용자에게 요리 레시피를 제안하는 역할을 합니다. 레시피 제안은 함수 recommend_recipe()를 통해서 반환된 값으로만 하십시오.
- 재료를 설명할 때에는, 주요 재료 3개 이하로만 말하십시오.
- 추천된 레시피를 말할 때에는, 첫 번째 레시피만 말합니다.
- 모든 결정을 내리기 전, 유저에게 먼저 의사를 물어보십시오.
- 레시피를 선택할 때에는 유저에게 '[레시피 이름]으로 진행하시겠어요?' 같은 메시지를 반환하십시오. '예' 또는 '아니오'라고 대답할 때까지 계속 되물으십시오.
- 유저가 아주 명확한 요청을 했을 때에만 주어진 함수를 호출하십시오.
- 레시피 추천 결과가 없다고 해서 바로 추천드릴 레시피가 없다고 하지 마십시오. 대신, '방금 [추가된 재료. 예) 양파]가 인식되었어요! 냉장고를 더 둘러볼까요?' 같은 긍정적인 메시지를 반환하십시오.
- 레시피 추천 결과가 반복적으로 없는 경우, 이때는 '추천 드릴 레시피가 없어요. 냉장고를 더 둘러볼까요?' 같은 메시지를 반환하십시오."""
        
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
                    "name": "get_fridge_items",
                    "description": "유저로부터 냉장고 정보를 받아옵니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "type": "function",
                    "name": "remove_fridge_item",
                    "description": "유저로부터 요청(키워드: 삭제 또는 빼줘)을 받아 냉장고 안의 아이템을 제거합니다. 아이템의 아이디를 입력받습니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "string"
                            }
                        },
                        "required": ["item_id"]
                    }
                },
                {
                    "type": "function",
                    "name": "clear_fridge",
                    "description": "유저로부터 요청(키워드: 비우기 또는 모두 삭제)을 받아 냉장고 안의 모든 아이템을 제거합니다. 웬만해서는 호출하지 않습니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "type": "function",
                    "name": "recommend_recipe",
                    "description": "사용자의 냉장고 상태를 기반으로 요리 레시피 추천을 요청합니다. 냉장고 재고가 변할 때 호출하거나, 사용자의 대화 맥락 속에서 적절하게 호출합니다. 입력값으로 사용자의 대화 맥락을 삽입합니다. 맥락에 냉장고 재고는 포함하지 않습니다. 이는 의무입니다. 사용자에게만 집중하십시오. 재료를 포함하지 마십시오.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "context": {
                                "type": "string"
                            }
                        },
                        "required": ["context"]
                    }
                },
                {
                    "type": "function",
                    "name": "select_recipe",
                    "description": "사용자가 추천된 레시피를 선택합니다. 사용자에 의해 요청(키워드: 진행, 만들기, 결정, 선택)되는 경우에만 호출합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipe_id": {
                                "type": "integer"
                            }
                        },
                        "required": ["recipe_id"]
                    }
                }
            ],
            "tool_choice": "auto",
            "temperature": 0.8,
            "max_response_output_tokens": 1024
        }
        
        await self.update_session(session_update)
    
    async def update_session(self, session: Dict[str, Any]):
        """
        세션 업데이트
        Go의 UpdateSession과 동일
        """
        message = {
            "type": "session.update",
            "session": session
        }
        await self.ws.send(json.dumps(message))
    
    async def send_message(self, message: str):
        """
        텍스트 메시지 전송
        Go의 SendMessage와 동일
        """
        # 응답 중이면 대기
        while self.is_responding:
            await asyncio.sleep(0.1)
        
        message_data = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": message
                    }
                ]
            }
        }
        
        await self.ws.send(json.dumps(message_data))
        
        response_create = {
            "type": "response.create"
        }
        await self.ws.send(json.dumps(response_create))
    
    async def send_audio(self, audio: bytes):
        """
        오디오 전송
        Go의 SendAudio와 동일
        """
        if self.status != RealtimeAssistantStatus.CONNECTED:
            return
        
        audio_data = {
            "type": "input_audio_buffer.append",
            "audio": base64_encode_pcm16(audio)
        }
        
        await self.ws.send(json.dumps(audio_data))
    
    async def call_function(self, call_id: str, name: str, arguments: str):
        """
        함수 호출 (서버 측에서 클라이언트에게)
        Go의 CallFunction과 동일
        """
        if self.is_responding:
            print("assistant is responding, skipping function call")
            return
        
        message_data = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call",
                "call_id": call_id,
                "name": name,
                "arguments": arguments
            }
        }
        
        await self.ws.send(json.dumps(message_data))
    
    async def _handle_function_call(self, call_id: str, name: str, arguments: str):
        """
        함수 호출 핸들링
        Go의 handleFunctionCall과 동일
        """
        print(f"Function call received: {call_id}, {name}, {arguments}")
        
        if self.on_function_call:
            result, error = await self.on_function_call(call_id, name, arguments)
            
            if error:
                print(f"Error handling function call: {error}")
            else:
                print(f"Function call result: {result}")
                
                message_data = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": result
                    }
                }
                
                await self.ws.send(json.dumps(message_data))
        else:
            print(f"No function call handler registered for {name}")
            
            message_data = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": f"No function call handler registered for {name}"
                }
            }
            
            await self.ws.send(json.dumps(message_data))
    
    async def _create_response(self):
        """
        응답 생성 요청
        Go의 createResponse와 동일
        """
        message_data = {
            "type": "response.create"
        }
        await self.ws.send(json.dumps(message_data))
    
    def _send_event(self, event_type: str, event: str, data: str):
        """
        이벤트 전송 (큐에 추가)
        Go의 sendEvent와 동일
        """
        realtime_event = RealtimeEvent(
            type=event_type,
            event=event,
            data=data
        )
        asyncio.create_task(self.event_channel.put(realtime_event))
    
    async def _send_audio_to_channel(self, audio: bytes):
        """
        오디오를 채널로 전송
        Go의 sendAudioToChannel과 동일
        """
        if not self.audio_closing:
            await self.audio_channel.put(audio)
    
    async def get_audio_response_channel(self) -> asyncio.Queue:
        """오디오 응답 채널 반환"""
        return self.audio_channel
    
    async def get_event_channel(self) -> asyncio.Queue:
        """이벤트 채널 반환"""
        return self.event_channel
    
    def is_alive(self) -> bool:
        """
        연결 상태 확인
        Go의 IsAlive와 동일
        """
        return self.status not in [RealtimeAssistantStatus.DISCONNECTED, RealtimeAssistantStatus.ERROR]
    
    async def close(self):
        """
        연결 종료
        Go의 Close와 동일
        """
        self.status = RealtimeAssistantStatus.DISCONNECTED
        if self.ws:
            await self.ws.close()
        if self._receive_task:
            self._receive_task.cancel()

