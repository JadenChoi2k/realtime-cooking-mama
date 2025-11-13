"""
Cooking Record Model
Complete port of Go's models/cook.go
"""
from pydantic import BaseModel
from datetime import datetime


class Cooking(BaseModel):
    """
    Cooking completion record
    Equivalent to Go's Cooking struct
    """
    recipe_id: int
    elapsed_seconds: int
    created_at: datetime
