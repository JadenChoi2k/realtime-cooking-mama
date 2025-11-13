"""
Event Models
Complete port of Go's models/chat_event.go
"""
from typing import Any
from pydantic import BaseModel


class YoriWebEvent(BaseModel):
    """
    YoriWebEvent represents events exchanged via WebSocket
    Equivalent to Go's YoriWebEvent struct
    """
    type: str  # "system", "assistant", "user"
    event: str
    data: Any
