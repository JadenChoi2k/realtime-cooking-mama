"""
OpenAI Assistant (for recipe recommendation)
Partial port of Go's ybcore/assistant.go + RecommendRecipe from yori_recipe.go
"""
from typing import List
import json
from openai import OpenAI
from core.fridge import FridgeItem


# Complete port of Go's recommendPrompt
RECOMMEND_PROMPT = """You must recommend between 0 to 5 recipes suitable for the user based on their context and fridge inventory. A recipe list will be provided for you to choose from. You will receive the user's current fridge inventory status and their context as input. Based on this, you will recommend a list of recipes. The recipe list is as follows:

**Recipe List Start**
{
  "food_ingredients": [
    {
      "id": "brown-egg",
      "name": "Egg",
      "is_in_fridge": true
    },
    {
      "id": "crab-meat",
      "name": "Crab Meat",
      "is_in_fridge": true
    },
    {
      "id": "morning-roll",
      "name": "Morning Roll",
      "is_in_fridge": false
    },
    {
      "id": "honey-mustard",
      "name": "Honey Mustard",
      "is_in_fridge": true
    },
    {
      "id": "mayonnaise",
      "name": "Mayonnaise",
      "is_in_fridge": true
    },
    {
      "id": "onion",
      "name": "Onion",
      "is_in_fridge": true
    },
    {
      "id": "strawberry-jam",
      "name": "Strawberry Jam",
      "is_in_fridge": true
    },
    {
      "id": "sweet-relish",
      "name": "Sweet Relish",
      "is_in_fridge": true
    },
    {
      "id": "white-egg",
      "name": "Boiled Egg",
      "is_in_fridge": true
    },
    {
      "id": "chicken-breast",
      "name": "Chicken Breast",
      "is_in_fridge": true
    },
    {
      "id": "salt",
      "name": "Salt",
      "is_in_fridge": false
    },
    {
      "id": "pepper",
      "name": "Pepper",
      "is_in_fridge": false
    },
    {
      "id": "spring-onion",
      "name": "Spring Onion",
      "is_in_fridge": true
    },
    {
      "id": "rice",
      "name": "Rice",
      "is_in_fridge": false
    },
    {
      "id": "cooking-oil",
      "name": "Cooking Oil",
      "is_in_fridge": false
    },
    {
      "id": "soy-sauce",
      "name": "Soy Sauce",
      "is_in_fridge": false
    },
    {
      "id": "oyster-sauce",
      "name": "Oyster Sauce",
      "is_in_fridge": false
    },
    {
      "id": "sesame-oil",
      "name": "Sesame Oil",
      "is_in_fridge": false
    }
  ],
  "recipes": [
    {
      "id": 1,
      "time": 10,
      "name": "Crab Meat Sandwich",
      "description": "Quick and delicious crab meat sandwich",
      "ingredients": [
        {"id": "morning-roll", "quantity": 2, "unit": "pieces", "required": true},
        {"id": "crab-meat", "quantity": 100, "unit": "g", "required": true},
        {"id": "brown-egg", "quantity": 1, "unit": "pieces", "required": true},
        {"id": "honey-mustard", "quantity": 1, "unit": "tablespoon", "required": false},
        {"id": "mayonnaise", "quantity": 2, "unit": "tablespoons", "required": false},
        {"id": "onion", "quantity": 30, "unit": "g", "required": false}
      ]
    },
    {
      "id": 2,
      "time": 5,
      "name": "Strawberry Jam Sandwich",
      "description": "Simple and sweet strawberry jam sandwich",
      "ingredients": [
        {"id": "morning-roll", "quantity": 2, "unit": "pieces", "required": true},
        {"id": "strawberry-jam", "quantity": 2, "unit": "tablespoons", "required": true}
      ]
    },
    {
      "id": 3,
      "time": 10,
      "name": "Deviled Egg",
      "description": "Classic deviled egg with mustard and sweet relish",
      "ingredients": [
        {"id": "white-egg", "quantity": 2, "unit": "pieces", "required": true},
        {"id": "honey-mustard", "quantity": 1, "unit": "teaspoon", "required": false},
        {"id": "mayonnaise", "quantity": 2, "unit": "tablespoons", "required": false},
        {"id": "sweet-relish", "quantity": 1, "unit": "teaspoon", "required": false}
      ]
    },
    {
      "id": 4,
      "time": 15,
      "name": "Egg Fried Rice",
      "description": "Savory egg fried rice",
      "ingredients": [
        {"id": "rice", "quantity": 200, "unit": "g", "required": true},
        {"id": "brown-egg", "quantity": 2, "unit": "pieces", "required": true},
        {"id": "spring-onion", "quantity": 20, "unit": "g", "required": false},
        {"id": "cooking-oil", "quantity": 1, "unit": "tablespoon", "required": true},
        {"id": "salt", "quantity": 1, "unit": "pinch", "required": false},
        {"id": "pepper", "quantity": 1, "unit": "pinch", "required": false}
      ]
    },
    {
      "id": 5,
      "time": 20,
      "name": "Chicken Stir-Fry",
      "description": "Savory chicken stir-fry with spring onions",
      "ingredients": [
        {"id": "chicken-breast", "quantity": 200, "unit": "g", "required": true},
        {"id": "spring-onion", "quantity": 50, "unit": "g", "required": true},
        {"id": "soy-sauce", "quantity": 2, "unit": "tablespoons", "required": true},
        {"id": "oyster-sauce", "quantity": 1, "unit": "tablespoon", "required": false},
        {"id": "sesame-oil", "quantity": 1, "unit": "teaspoon", "required": false},
        {"id": "cooking-oil", "quantity": 1, "unit": "tablespoon", "required": true}
      ]
    }
  ]
}
**Recipe List End**

is_in_fridge indicates whether each ingredient is currently in the fridge. Each recipe has required and non-required (optional) ingredients. The more ingredients from the required list that are in the fridge, the more likely the recipe should be recommended. However, recipes should NOT be recommended if required ingredients are not present.

If there are no recommendable recipes, return an empty list `{"recipes": []}`. Otherwise, return the recommended recipes in the following format:
- Return format: {"recipes": [{"id": 1, "reason": "..."}, {"id": 3, "reason": "..."}]}
- You must include the reason field. The reason should be a brief explanation in one or two sentences about why the recipe is recommended."""


class OpenAIAssistant:
    """
    OpenAI Assistant (for recipe recommendation)
    Partial implementation of Go's OpenAIAssistant
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Args:
            api_key: OpenAI API key
            model: Model name
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = ""
    
    def set_system_prompt(self, prompt: str):
        """Set system prompt"""
        self.system_prompt = prompt
    
    async def handle_with_json(self, message: str, response_format: dict) -> str:
        """
        Request with Structured Output
        Same as Go's HandleWithJSON
        
        Args:
            message: User message
            response_format: JSON schema
        
        Returns:
            JSON string
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": response_format
            }
        )
        
        return response.choices[0].message.content


async def recommend_recipe(openai_key: str, fridge_items: List[FridgeItem], context: str) -> List[int]:
    """
    Recipe recommendation
    Complete port of Go's RecommendRecipe function
    
    Args:
        openai_key: OpenAI API key
        fridge_items: List of fridge items
        context: User context
    
    Returns:
        List of recommended recipe IDs
    """
    assistant = OpenAIAssistant(openai_key, "gpt-4o")
    assistant.set_system_prompt(RECOMMEND_PROMPT)
    
    # Convert fridge items to JSON
    fridge_json = json.dumps([item.model_dump() for item in fridge_items])
    
    # Create message
    message = f"1. Fridge: {fridge_json}\n2. Context: {context}"
    
    # Structured Output schema (same as Go)
    response_format = {
        "name": "recommended",
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["recipe"],
            "properties": {
                "recipe": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Recipe ID"
                }
            },
            "additionalProperties": False
        }
    }
    
    # API call
    response_str = await assistant.handle_with_json(message, response_format)
    
    # Parse
    response_json = json.loads(response_str)
    recipes = response_json.get("recipe", [])
    
    return recipes

