"""
레시피 모델
Go의 models/recipe.go 완벽 복제
"""
from pydantic import BaseModel
from typing import List


class Ingredient(BaseModel):
    """
    식재료 정보
    Go의 Ingredient 구조체와 동일
    """
    id: str
    name: str
    is_in_fridge: bool


class RecipeIngredient(BaseModel):
    """
    레시피에 사용되는 식재료와 수량
    Go의 RecipeIngredient 구조체와 동일
    """
    id: str
    quantity: int
    unit: str
    required: bool


class RecipeStep(BaseModel):
    """
    레시피 단계
    Go의 RecipeStep 구조체와 동일
    """
    order: int
    title: str
    description: str


class Recipe(BaseModel):
    """
    레시피 정보
    Go의 Recipe 구조체와 동일
    """
    id: int
    time: int
    name: str
    description: str
    ingredients: List[RecipeIngredient]
    steps: List[RecipeStep]

