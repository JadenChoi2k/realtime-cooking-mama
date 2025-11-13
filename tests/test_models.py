"""
데이터 모델 테스트
Go 서버의 models 패키지 동작을 검증
"""
import pytest
from datetime import datetime
from models.events import YoriWebEvent
from models.recipe import Ingredient, RecipeIngredient, RecipeStep, Recipe
from models.cooking import Cooking


class TestYoriWebEvent:
    """YoriWebEvent 모델 테스트"""
    
    def test_create_system_event(self):
        """시스템 이벤트 생성 테스트"""
        event = YoriWebEvent(
            type="system",
            event="password",
            data="Please enter your password"
        )
        assert event.type == "system"
        assert event.event == "password"
        assert event.data == "Please enter your password"
    
    def test_create_assistant_event(self):
        """어시스턴트 이벤트 생성 테스트"""
        event = YoriWebEvent(
            type="assistant",
            event="transcript",
            data="안녕하세요"
        )
        assert event.type == "assistant"
        assert event.event == "transcript"
    
    def test_create_user_event_with_list(self):
        """사용자 이벤트 (리스트 데이터) 생성 테스트"""
        detections = [
            {"class": "brown-egg", "confidence": 0.9},
            {"class": "crab-meat", "confidence": 0.85}
        ]
        event = YoriWebEvent(
            type="user",
            event="object_detection",
            data=detections
        )
        assert event.type == "user"
        assert event.event == "object_detection"
        assert len(event.data) == 2
    
    def test_json_serialization(self):
        """JSON 직렬화 테스트"""
        event = YoriWebEvent(
            type="assistant",
            event="message",
            data="테스트 메시지"
        )
        json_data = event.model_dump()
        assert json_data["type"] == "assistant"
        assert json_data["event"] == "message"
        assert json_data["data"] == "테스트 메시지"


class TestRecipeModels:
    """레시피 관련 모델 테스트"""
    
    def test_create_ingredient(self):
        """식재료 생성 테스트"""
        ingredient = Ingredient(
            id="brown-egg",
            name="달걀",
            is_in_fridge=True
        )
        assert ingredient.id == "brown-egg"
        assert ingredient.name == "달걀"
        assert ingredient.is_in_fridge is True
    
    def test_create_recipe_ingredient(self):
        """레시피 식재료 생성 테스트"""
        recipe_ing = RecipeIngredient(
            id="brown-egg",
            quantity=4,
            unit="개",
            required=True
        )
        assert recipe_ing.id == "brown-egg"
        assert recipe_ing.quantity == 4
        assert recipe_ing.unit == "개"
        assert recipe_ing.required is True
    
    def test_create_recipe_step(self):
        """레시피 단계 생성 테스트"""
        step = RecipeStep(
            order=1,
            title="양파 다지기",
            description="양파 1/4를 다져서 준비합니다."
        )
        assert step.order == 1
        assert step.title == "양파 다지기"
        assert "양파" in step.description
    
    def test_create_recipe(self):
        """레시피 생성 테스트"""
        ingredients = [
            RecipeIngredient(id="crab-meat", quantity=4, unit="ea", required=True),
            RecipeIngredient(id="onion", quantity=1, unit="/4", required=True)
        ]
        steps = [
            RecipeStep(order=1, title="준비", description="재료를 준비합니다."),
            RecipeStep(order=2, title="조리", description="조리를 시작합니다.")
        ]
        
        recipe = Recipe(
            id=1,
            time=10,
            name="게살 샌드위치",
            description="게맛살의 크리미한 식감과 허니 머스타드의 달콤함이 만나 더욱 풍부한 맛을 즐길 수 있어요!",
            ingredients=ingredients,
            steps=steps
        )
        
        assert recipe.id == 1
        assert recipe.time == 10
        assert recipe.name == "게살 샌드위치"
        assert len(recipe.ingredients) == 2
        assert len(recipe.steps) == 2
        assert recipe.ingredients[0].id == "crab-meat"
        assert recipe.steps[0].order == 1


class TestCooking:
    """요리 기록 모델 테스트"""
    
    def test_create_cooking(self):
        """요리 기록 생성 테스트"""
        now = datetime.now()
        cooking = Cooking(
            recipe_id=1,
            elapsed_seconds=600,
            created_at=now
        )
        assert cooking.recipe_id == 1
        assert cooking.elapsed_seconds == 600
        assert cooking.created_at == now
    
    def test_cooking_json_serialization(self):
        """요리 기록 JSON 직렬화 테스트"""
        now = datetime.now()
        cooking = Cooking(
            recipe_id=1,
            elapsed_seconds=600,
            created_at=now
        )
        json_data = cooking.model_dump()
        assert json_data["recipe_id"] == 1
        assert json_data["elapsed_seconds"] == 600
        assert isinstance(json_data["created_at"], datetime)

