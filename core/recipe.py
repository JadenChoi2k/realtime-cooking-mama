"""
레시피 관리
Go의 ybcore/yori_recipe.go 완벽 복제
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from models.recipe import Ingredient, Recipe, RecipeIngredient, RecipeStep


class RecipeSource:
    """
    레시피 소스 (JSON 데이터 관리)
    Go의 RecipeSource 구조체와 동일
    """
    
    def __init__(self, json_data: dict):
        """
        Args:
            json_data: recipe.json 데이터
        """
        self.ingredients: Dict[str, Ingredient] = {}
        self.recipes: List[Recipe] = []
        
        # 식재료 파싱
        food_ingredients = json_data.get("food_ingredients", [])
        for item in food_ingredients:
            ingredient = Ingredient(
                id=item["id"],
                name=item["name"],
                is_in_fridge=item["is_in_fridge"]
            )
            self.ingredients[ingredient.id] = ingredient
        
        # 레시피 파싱
        recipes = json_data.get("recipes", [])
        for item in recipes:
            # 식재료 파싱
            recipe_ingredients = []
            for ing in item.get("ingredients", []):
                recipe_ingredient = RecipeIngredient(
                    id=ing["id"],
                    quantity=ing["quantity"],
                    unit=ing["unit"],
                    required=ing["required"]
                )
                recipe_ingredients.append(recipe_ingredient)
            
            # 단계 파싱
            steps = []
            for step in item.get("steps", []):
                recipe_step = RecipeStep(
                    order=step["order"],
                    title=step["title"],
                    description=step["description"]
                )
                steps.append(recipe_step)
            
            # 레시피 생성
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
        식재료 ID로 조회
        Go의 GetIngredientByID와 동일
        
        Args:
            id: 식재료 ID
        
        Returns:
            Ingredient 또는 None
        """
        return self.ingredients.get(id)
    
    def get_recipes_by_ids(self, ids: List[int]) -> List[Recipe]:
        """
        레시피 ID 리스트로 여러 레시피 조회
        Go의 GetRecipesByIDs와 동일
        
        Args:
            ids: 레시피 ID 리스트
        
        Returns:
            Recipe 리스트
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
        레시피 ID로 조회
        Go의 GetRecipeByID와 동일
        
        Args:
            id: 레시피 ID
        
        Returns:
            Recipe 또는 None
        """
        for recipe in self.recipes:
            if recipe.id == id:
                return recipe
        return None


class RecipeHelper:
    """
    레시피 진행 도우미
    Go의 RecipeHelper 구조체와 동일
    """
    
    def __init__(self, recipe: Recipe):
        """
        Args:
            recipe: Recipe 인스턴스
        """
        self.current_step = 0
        self.recipe = recipe
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.done_flag = False
    
    def get_recipe(self) -> Recipe:
        """
        레시피 반환
        Go의 GetRecipe와 동일
        """
        return self.recipe
    
    def get_current_step(self) -> RecipeStep:
        """
        현재 단계 반환
        Go의 GetCurrentStep과 동일
        currentStep <= 0일 때 "요리 준비" 단계 반환
        
        Returns:
            RecipeStep
        """
        if self.current_step <= 0:
            return RecipeStep(
                order=1,
                title="요리 준비",
                description="요리를 준비합니다. 시작할 준비가 되면 알려주세요."
            )
        return self.recipe.steps[self.current_step - 1]
    
    def go_previous_step(self) -> RecipeStep:
        """
        이전 단계로 이동
        Go의 GoPreviousStep과 동일
        
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
        다음 단계로 이동
        Go의 GoNextStep과 동일
        
        Returns:
            (RecipeStep, is_last)
        """
        if self.current_step < len(self.recipe.steps):
            self.current_step += 1
        
        is_last = (self.current_step == len(self.recipe.steps))
        return self.recipe.steps[self.current_step - 1], is_last
    
    def mark_done(self) -> bool:
        """
        요리 완료 표시
        Go의 Done 함수와 동일
        
        Returns:
            완료 여부 (마지막 단계가 아니면 False)
        """
        if self.current_step < len(self.recipe.steps):
            return False
        
        self.done_flag = True
        self.end_time = datetime.now()
        return True
    
    def get_elapsed_time(self) -> timedelta:
        """
        경과 시간 반환
        Go의 GetElapsedTime과 동일
        
        Returns:
            timedelta
        """
        if self.end_time is None:
            return datetime.now() - self.start_time
        return self.end_time - self.start_time
    
    def get_elapsed_time_string(self) -> str:
        """
        경과 시간 문자열 반환
        Go의 GetElapsedTimeString과 동일
        
        Returns:
            경과 시간 문자열
        """
        if self.end_time is None:
            return "아직 요리 중입니다."
        
        duration = self.get_elapsed_time()
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        seconds = int(duration.total_seconds() % 60)
        
        return f"경과 시간: {hours}시간 {minutes}분 {seconds}초"

