"""
Recipe Models
Complete port of Go's models/recipe.go
"""
from pydantic import BaseModel
from typing import List


class Ingredient(BaseModel):
    """
    Ingredient information
    Equivalent to Go's Ingredient struct
    """
    id: str
    name: str
    is_in_fridge: bool


class RecipeIngredient(BaseModel):
    """
    Ingredient with quantity used in recipe
    Equivalent to Go's RecipeIngredient struct
    """
    id: str
    quantity: int
    unit: str
    required: bool


class RecipeStep(BaseModel):
    """
    Recipe step information
    Equivalent to Go's RecipeStep struct
    """
    order: int
    title: str
    description: str


class Recipe(BaseModel):
    """
    Recipe information
    Equivalent to Go's Recipe struct
    """
    id: int
    time: int
    name: str
    description: str
    ingredients: List[RecipeIngredient]
    steps: List[RecipeStep]
