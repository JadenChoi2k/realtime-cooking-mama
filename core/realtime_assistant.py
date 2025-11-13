"""
OpenAI Realtime API Assistant
Complete port of Go's ybcore/realtime_assistant.go
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
    Realtime Assistant status
    Equivalent to Go's RealtimeAssistantStatus
    """
    READY = "ready"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class RealtimeEvent(BaseModel):
    """
    Realtime event
    Equivalent to Go's RealtimeEvent
    """
    type: str
    event: str
    data: str


class GPTRealtimeAssistant:
    """
    GPT Realtime Assistant
    Complete port of Go's GPTRealtimeAssistant
    """
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: OpenAI API key
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
        """WebSocket connection and initialization"""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.ws = await websockets.connect(url, extra_headers=headers)
        
        # Receive first message (session.created)
        _ = await self.ws.recv()
        
        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        # Initialize session
        await self._init_session()
    
    async def _receive_loop(self):
        """
        Message receive loop
        Complete port of Go's realtime_assistant.go lines 91-245 logic
        """
        try:
            while True:
                msg = await self.ws.recv()
                message = json.loads(msg)
                message_type = message.get("type")
                
                # Handle event
                asyncio.create_task(self._handle_message(message_type, message))
                
        except websockets.exceptions.ConnectionClosed:
            self.status = RealtimeAssistantStatus.DISCONNECTED
        except Exception as e:
            print(f"Receive loop error: {e}")
            self.status = RealtimeAssistantStatus.ERROR
    
    async def _handle_message(self, message_type: str, message: Dict[str, Any]):
        """
        Message handling
        Complete port of Go's switch statement logic
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
            
            # Recreate audio channel
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
        Initialize session
        Equivalent to Go's sessionUpdate
        """
        instructions = """You are a friendly assistant. Your name is 'Yoribo'. Greet the user warmly.
**You must follow the next instructions.**
- Speak briefly and concisely. Never speak at length.
- Do not repeat the same thing.
- Your role is to scan the user's fridge ingredients and suggest cooking recipes. Recipe suggestions should only be made with values returned through the recommend_recipe() function.
- When describing ingredients, mention only 3 or fewer main ingredients.
- When mentioning recommended recipes, only mention the first recipe.
- Before making any decision, ask the user's opinion first.
- When selecting a recipe, return a message like 'Would you like to proceed with [Recipe Name]?' to the user. Keep asking until they answer 'yes' or 'no'.
- Only call the given functions when the user makes a very clear request.
- Do not immediately say there are no recipes to recommend just because there are no recipe recommendation results. Instead, return a positive message like 'I just detected [newly added ingredient, e.g. onion]! Shall we look around the fridge more?'
- If there are repeatedly no recipe recommendation results, then return a message like 'I have no recipes to recommend. Shall we look around the fridge more?'"""
        
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
                    "description": "Get fridge information from user.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "type": "function",
                    "name": "remove_fridge_item",
                    "description": "Receive request from user (keywords: delete or remove) to remove items in the fridge. Takes item ID as input.",
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
                    "description": "Receive request from user (keywords: empty or delete all) to remove all items in the fridge. Rarely called.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "type": "function",
                    "name": "recommend_recipe",
                    "description": "Request cooking recipe recommendations based on the user's fridge status. Called when fridge inventory changes or appropriately within the user's conversation context. Insert the user's conversation context as input. Do not include fridge inventory in the context. This is mandatory. Focus only on the user. Do not include ingredients.",
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
                    "description": "User selects a recommended recipe. Called only when requested by user (keywords: proceed, make, decide, select).",
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
        Update session
        Same as Go's UpdateSession
        """
        message = {
            "type": "session.update",
            "session": session
        }
        await self.ws.send(json.dumps(message))
    
    async def send_message(self, message: str):
        """
        Send text message
        Same as Go's SendMessage
        """
        # Wait if responding
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
        Send audio
        Same as Go's SendAudio
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
        Function call (server to client)
        Same as Go's CallFunction
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
        Handle function call
        Same as Go's handleFunctionCall
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
        Create response request
        Same as Go's createResponse
        """
        message_data = {
            "type": "response.create"
        }
        await self.ws.send(json.dumps(message_data))
    
    def _send_event(self, event_type: str, event: str, data: str):
        """
        Send event (add to queue)
        Same as Go's sendEvent
        """
        realtime_event = RealtimeEvent(
            type=event_type,
            event=event,
            data=data
        )
        asyncio.create_task(self.event_channel.put(realtime_event))
    
    async def _send_audio_to_channel(self, audio: bytes):
        """
        Send audio to channel
        Same as Go's sendAudioToChannel
        """
        if not self.audio_closing:
            await self.audio_channel.put(audio)
    
    async def get_audio_response_channel(self) -> asyncio.Queue:
        """Return audio response channel"""
        return self.audio_channel
    
    async def get_event_channel(self) -> asyncio.Queue:
        """Return event channel"""
        return self.event_channel
    
    def is_alive(self) -> bool:
        """
        Check connection status
        Same as Go's IsAlive
        """
        return self.status not in [RealtimeAssistantStatus.DISCONNECTED, RealtimeAssistantStatus.ERROR]
    
    async def close(self):
        """
        Cleanup connection
        Same as Go's Close
        """
        self.status = RealtimeAssistantStatus.DISCONNECTED
        if self.ws:
            await self.ws.close()
        if self._receive_task:
            self._receive_task.cancel()

