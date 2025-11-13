"""
Recipe Management
Complete port of Go's ybcore/yori_recipe.go
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from models.recipe import Ingredient, Recipe, RecipeIngredient, RecipeStep


class RecipeSource:
    """
    Recipe source (manages JSON data)
    Equivalent to Go's RecipeSource struct
    """
    
    def __init__(self, json_data: dict):
        """
        Args:
            json_data: recipe.json data
        """
        self.ingredients: Dict[str, Ingredient] = {}
        self.recipes: List[Recipe] = []
        
        # Parse ingredients
        food_ingredients = json_data.get("food_ingredients", [])
        for item in food_ingredients:
            ingredient = Ingredient(
                id=item["id"],
                name=item["name"],
                is_in_fridge=item["is_in_fridge"]
            )
            self.ingredients[ingredient.id] = ingredient
        
        # Parse recipes
        recipes = json_data.get("recipes", [])
        for item in recipes:
            # Parse ingredients
            recipe_ingredients = []
            for ing in item.get("ingredients", []):
                recipe_ingredient = RecipeIngredient(
                    id=ing["id"],
                    quantity=ing["quantity"],
                    unit=ing["unit"],
                    required=ing["required"]
                )
                recipe_ingredients.append(recipe_ingredient)
            
            # Parse steps
            steps = []
            for step in item.get("steps", []):
                recipe_step = RecipeStep(
                    order=step["order"],
                    title=step["title"],
                    description=step["description"]
                )
                steps.append(recipe_step)
            
            # Create recipe
            recipe = Recipe(
                id=item["id"],
                time=item["time"],
                name=item["name"],
                description=item["description"],
                ingredients=recipe_ingredients,
                steps=steps
            )
            self.recipes.append(recipe)
    
    def get_ingredient_by_id(self, id: str) -> Optional[Ingredient]:
        """
        Get ingredient by ID
        Same as Go's GetIngredientByID
        
        Args:
            id: Ingredient ID
        
        Returns:
            Ingredient or None
        """
        return self.ingredients.get(id)
    
    def get_recipes_by_ids(self, ids: List[int]) -> List[Recipe]:
        """
        Get multiple recipes by ID list
        Same as Go's GetRecipesByIDs
        
        Args:
            ids: Recipe ID list
        
        Returns:
            List of recipes
        """
        recipes = []
        for recipe_id in ids:
            for recipe in self.recipes:
                if recipe.id == recipe_id:
                    recipes.append(recipe)
                    break
        return recipes
    
    def get_recipe_by_id(self, id: int) -> Optional[Recipe]:
        """
        Get recipe by ID
        Same as Go's GetRecipeByID
        
        Args:
            id: Recipe ID
        
        Returns:
            Recipe or None
        """
        for recipe in self.recipes:
            if recipe.id == id:
                return recipe
        return None


class RecipeHelper:
    """
    Recipe progress helper
    Equivalent to Go's RecipeHelper struct
    """
    
    def __init__(self, recipe: Recipe):
        """
        Args:
            recipe: Recipe instance
        """
        self.current_step = 0
        self.recipe = recipe
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.done_flag = False
    
    def get_recipe(self) -> Recipe:
        """
        Return recipe
        Same as Go's GetRecipe
        """
        return self.recipe
    
    def get_current_step(self) -> RecipeStep:
        """
        Return current step
        Same as Go's GetCurrentStep
        Return "Preparation" step when currentStep <= 0
        
        Returns:
            RecipeStep
        """
        if self.current_step <= 0:
            return RecipeStep(
                order=1,
                title="Preparation",
                description="Prepare for cooking. Let me know when you're ready to start."
            )
        return self.recipe.steps[self.current_step - 1]
    
    def go_previous_step(self) -> RecipeStep:
        """
        Move to previous step
        Same as Go's GoPreviousStep
        
        Returns:
            RecipeStep
        """
        if self.current_step <= 1:
            self.current_step = 1
            return self.recipe.steps[0]
        
        self.current_step -= 1
        return self.recipe.steps[self.current_step - 1]
    
    def go_next_step(self) -> Tuple[RecipeStep, bool]:
        """
        Move to next step
        Same as Go's GoNextStep
        
        Returns:
            (RecipeStep, is_last)
        """
        if self.current_step < len(self.recipe.steps):
            self.current_step += 1
        
        is_last = (self.current_step == len(self.recipe.steps))
        return self.recipe.steps[self.current_step - 1], is_last
    
    def mark_done(self) -> bool:
        """
        Mark cooking as complete
        Same as Go's Done function
        
        Returns:
            Completion status (False if not last step)
        """
        if self.current_step < len(self.recipe.steps):
            return False
        
        self.done_flag = True
        self.end_time = datetime.now()
        return True
    
    def get_elapsed_time(self) -> timedelta:
        """
        Return elapsed time
        Same as Go's GetElapsedTime
        
        Returns:
            timedelta
        """
        if self.end_time is None:
            return datetime.now() - self.start_time
        return self.end_time - self.start_time
    
    def get_elapsed_time_string(self) -> str:
        """
        Return elapsed time string
        Same as Go's GetElapsedTimeString
        
        Returns:
            Elapsed time string
        """
        if self.end_time is None:
            return "Still cooking."
        
        duration = self.get_elapsed_time()
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        seconds = int(duration.total_seconds() % 60)
        
        return f"Elapsed time: {hours}h {minutes}m {seconds}s"

