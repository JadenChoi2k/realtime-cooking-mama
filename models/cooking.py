"""
요리 기록 모델
Go의 models/cook.go 완벽 복제
"""
from pydantic import BaseModel
from datetime import datetime


class Cooking(BaseModel):
    """
    요리 완료 기록
    Go의 Cooking 구조체와 동일
    """
    recipe_id: int
    elapsed_seconds: int
    created_at: datetime

