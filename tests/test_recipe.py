"""
레시피 로직 테스트
Go 서버의 ybcore/yori_recipe.go 동작을 Validate
"""
import pytest
from datetime import datetime, timedelta
from core.recipe import RecipeSource, RecipeHelper
from models.recipe import Recipe, RecipeIngredient, RecipeStep


@pytest.fixture
def sample_recipe_json():
    """테스트용 레시피 JSON 데이터"""
    return {
        "food_ingredients": [
            {"id": "brown-egg", "name": "달걀", "is_in_fridge": True},
            {"id": "crab-meat", "name": "게맛살", "is_in_fridge": True},
            {"id": "onion", "name": "양파", "is_in_fridge": True},
            {"id": "morning-roll", "name": "모닝빵", "is_in_fridge": False}
        ],
        "recipes": [
            {
                "id": 1,
                "name": "게살 샌드위치",
                "time": 10,
                "description": "게맛살의 크리미한 식감",
                "ingredients": [
                    {"id": "morning-roll", "quantity": 2, "unit": "개", "required": True},
                    {"id": "crab-meat", "quantity": 4, "unit": "ea", "required": True},
                    {"id": "onion", "quantity": 1, "unit": "/4", "required": True}
                ],
                "steps": [
                    {"order": 1, "title": "준비", "description": "양파를 다집니다."},
                    {"order": 2, "title": "섞기", "description": "재료를 섞습니다."},
                    {"order": 3, "title": "완성", "description": "빵에 채웁니다."}
                ]
            },
            {
                "id": 2,
                "name": "계란말이",
                "time": 15,
                "description": "달걀 요리",
                "ingredients": [
                    {"id": "brown-egg", "quantity": 4, "unit": "개", "required": True}
                ],
                "steps": [
                    {"order": 1, "title": "준비", "description": "달걀을 푼다."},
                    {"order": 2, "title": "조리", "description": "팬에 굽는다."}
                ]
            }
        ]
    }


class TestRecipeSource:
    """RecipeSource 테스트"""
    
    def test_init(self, sample_recipe_json):
        """RecipeSource Initialize 테스트"""
        source = RecipeSource(sample_recipe_json)
        assert len(source.ingredients) == 4
        assert len(source.recipes) == 2
    
    def test_get_ingredient_by_id(self, sample_recipe_json):
        """식재료 ID로 Get/Retrieve"""
        source = RecipeSource(sample_recipe_json)
        
        ingredient = source.get_ingredient_by_id("brown-egg")
        assert ingredient is not None
        assert ingredient.name == "달걀"
        assert ingredient.is_in_fridge is True
    
    def test_get_ingredient_by_id_not_found(self, sample_recipe_json):
        """존재하지 않는 식재료 Get/Retrieve"""
        source = RecipeSource(sample_recipe_json)
        
        ingredient = source.get_ingredient_by_id("unknown")
        assert ingredient is None
    
    def test_get_recipe_by_id(self, sample_recipe_json):
        """레시피 ID로 Get/Retrieve"""
        source = RecipeSource(sample_recipe_json)
        
        recipe = source.get_recipe_by_id(1)
        assert recipe is not None
        assert recipe.name == "게살 샌드위치"
        assert len(recipe.ingredients) == 3
        assert len(recipe.steps) == 3
    
    def test_get_recipes_by_ids(self, sample_recipe_json):
        """여러 레시피 ID로 Get/Retrieve"""
        source = RecipeSource(sample_recipe_json)
        
        recipes = source.get_recipes_by_ids([1, 2])
        assert len(recipes) == 2
        assert recipes[0].id == 1
        assert recipes[1].id == 2


class TestRecipeHelper:
    """RecipeHelper 테스트"""
    
    @pytest.fixture
    def sample_recipe(self):
        """테스트용 레시피"""
        return Recipe(
            id=1,
            time=10,
            name="게살 샌드위치",
            description="테스트",
            ingredients=[],
            steps=[
                RecipeStep(order=1, title="1단계", description="첫 번째 단계"),
                RecipeStep(order=2, title="2단계", description="두 번째 단계"),
                RecipeStep(order=3, title="3단계", description="세 번째 단계")
            ]
        )
    
    def test_init(self, sample_recipe):
        """RecipeHelper Initialize 테스트"""
        helper = RecipeHelper(sample_recipe)
        assert helper.current_step == 0
        assert helper.done_flag is False
    
    def test_get_current_step_before_start(self, sample_recipe):
        """Start 전 현재 단계 (currentStep <= 0일 때 "요리 준비" Returns)"""
        helper = RecipeHelper(sample_recipe)
        
        step = helper.get_current_step()
        assert step.order == 1
        assert step.title == "요리 준비"
        assert "준비" in step.description
    
    def test_go_next_step(self, sample_recipe):
        """next 단계로 이동"""
        helper = RecipeHelper(sample_recipe)
        
        # 1단계로 이동
        step, is_last = helper.go_next_step()
        assert step.order == 1
        assert step.title == "1단계"
        assert is_last is False
        
        # 2단계로 이동
        step, is_last = helper.go_next_step()
        assert step.order == 2
        assert is_last is False
        
        # 3단계로 이동 (마지막)
        step, is_last = helper.go_next_step()
        assert step.order == 3
        assert is_last is True
    
    def test_go_previous_step(self, sample_recipe):
        """previous 단계로 이동"""
        helper = RecipeHelper(sample_recipe)
        
        # 3단계까지 이동
        helper.go_next_step()
        helper.go_next_step()
        helper.go_next_step()
        
        # 2단계로 돌아가기
        step = helper.go_previous_step()
        assert step.order == 2
        
        # 1단계로 돌아가기
        step = helper.go_previous_step()
        assert step.order == 1
        
        # 1단계에서 더 previous으로 가려고 하면 1단계 유지
        step = helper.go_previous_step()
        assert step.order == 1
    
    def test_done_before_last_step(self, sample_recipe):
        """마지막 단계 전에 complete 시도"""
        helper = RecipeHelper(sample_recipe)
        
        helper.go_next_step()  # 1단계
        
        result = helper.mark_done()
        assert result is False
        assert helper.done_flag is False
    
    def test_done_at_last_step(self, sample_recipe):
        """마지막 단계에서 complete"""
        helper = RecipeHelper(sample_recipe)
        
        helper.go_next_step()  # 1단계
        helper.go_next_step()  # 2단계
        helper.go_next_step()  # 3단계 (마지막)
        
        result = helper.mark_done()
        assert result is True
        assert helper.done_flag is True
        assert helper.end_time is not None
    
    def test_get_elapsed_time(self, sample_recipe):
        """경과 시간 계산"""
        import time
        helper = RecipeHelper(sample_recipe)
        
        time.sleep(0.1)  # 0.1초 대기
        
        elapsed = helper.get_elapsed_time()
        assert elapsed.total_seconds() >= 0.1
        assert helper.end_time is None  # 아직 complete 안 함
    
    def test_get_elapsed_time_after_done(self, sample_recipe):
        """complete 후 경과 시간"""
        import time
        helper = RecipeHelper(sample_recipe)
        
        helper.go_next_step()
        helper.go_next_step()
        helper.go_next_step()
        
        time.sleep(0.1)
        helper.mark_done()
        
        elapsed1 = helper.get_elapsed_time()
        time.sleep(0.1)
        elapsed2 = helper.get_elapsed_time()
        
        # complete 후에는 시간이 고정됨
        assert abs(elapsed1.total_seconds() - elapsed2.total_seconds()) < 0.01
    
    def test_get_elapsed_time_string(self, sample_recipe):
        """경과 시간 string"""
        helper = RecipeHelper(sample_recipe)
        
        # complete 전
        time_str = helper.get_elapsed_time_string()
        assert "아직 요리 중입니다" in time_str
        
        # complete 후
        helper.go_next_step()
        helper.go_next_step()
        helper.go_next_step()
        helper.mark_done()
        
        time_str = helper.get_elapsed_time_string()
        assert "경과 시간" in time_str
        assert "시간" in time_str
        assert "분" in time_str
        assert "초" in time_str

