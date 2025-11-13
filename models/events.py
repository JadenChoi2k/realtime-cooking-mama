"""
이벤트 모델
Go의 models/chat_event.go 완벽 복제
"""
from typing import Any
from pydantic import BaseModel


class YoriWebEvent(BaseModel):
    """
    YoriWebEvent는 WebSocket을 통해 주고받는 이벤트
    Go의 YoriWebEvent 구조체와 동일
    """
    type: str  # "system", "assistant", "user"
    event: str
    data: Any

