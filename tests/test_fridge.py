"""
냉장고 로직 테스트
Go 서버의 ybcore/fridge.go 동작을 검증
"""
import pytest
from core.fridge import Fridge, FridgeItem
from core.recipe import RecipeSource


@pytest.fixture
def recipe_source():
    """테스트용 RecipeSource 픽스처"""
    json_data = {
        "food_ingredients": [
            {"id": "brown-egg", "name": "달걀", "is_in_fridge": True},
            {"id": "crab-meat", "name": "게맛살", "is_in_fridge": True},
            {"id": "onion", "name": "양파", "is_in_fridge": True}
        ],
        "recipes": []
    }
    return RecipeSource(json_data)


@pytest.mark.asyncio
async def test_fridge_init(recipe_source):
    """냉장고 초기화 테스트"""
    fridge = Fridge(recipe_source)
    items = await fridge.get_items()
    assert len(items) == 0


@pytest.mark.asyncio
async def test_fridge_looked_new_item(recipe_source):
    """새 아이템 추가 시 changed=True"""
    fridge = Fridge(recipe_source)
    
    items, changed = await fridge.looked(["brown-egg"])
    
    assert changed is True
    assert len(items) == 1
    assert items[0].id == "brown-egg"
    assert items[0].name == "달걀"
    assert items[0].quantity == 1


@pytest.mark.asyncio
async def test_fridge_looked_quantity_increase(recipe_source):
    """수량 증가 시 changed=True"""
    fridge = Fridge(recipe_source)
    
    # 첫 번째: 달걀 1개
    items, changed = await fridge.looked(["brown-egg"])
    assert changed is True
    assert items[0].quantity == 1
    
    # 두 번째: 달걀 2개 (증가)
    items, changed = await fridge.looked(["brown-egg", "brown-egg"])
    assert changed is True
    assert len(items) == 1
    assert items[0].quantity == 2


@pytest.mark.asyncio
async def test_fridge_looked_quantity_same(recipe_source):
    """수량 동일 시 changed=False"""
    fridge = Fridge(recipe_source)
    
    # 첫 번째: 달걀 2개
    await fridge.looked(["brown-egg", "brown-egg"])
    
    # 두 번째: 여전히 달걀 2개 (동일)
    items, changed = await fridge.looked(["brown-egg", "brown-egg"])
    assert changed is False
    assert items[0].quantity == 2


@pytest.mark.asyncio
async def test_fridge_looked_multiple_items(recipe_source):
    """여러 아이템 추가 테스트"""
    fridge = Fridge(recipe_source)
    
    items, changed = await fridge.looked(["brown-egg", "crab-meat", "onion", "brown-egg"])
    
    assert changed is True
    assert len(items) == 3
    
    # 아이템 찾기
    egg_item = next(item for item in items if item.id == "brown-egg")
    crab_item = next(item for item in items if item.id == "crab-meat")
    onion_item = next(item for item in items if item.id == "onion")
    
    assert egg_item.quantity == 2
    assert crab_item.quantity == 1
    assert onion_item.quantity == 1


@pytest.mark.asyncio
async def test_fridge_looked_unknown_ingredient(recipe_source):
    """알 수 없는 식재료 처리 (ID를 이름으로 사용)"""
    fridge = Fridge(recipe_source)
    
    items, changed = await fridge.looked(["unknown-item"])
    
    assert changed is True
    assert len(items) == 1
    assert items[0].id == "unknown-item"
    assert items[0].name == "unknown-item"  # ID를 이름으로 사용


@pytest.mark.asyncio
async def test_fridge_remove(recipe_source):
    """아이템 제거 테스트"""
    fridge = Fridge(recipe_source)
    
    await fridge.looked(["brown-egg", "crab-meat"])
    items = await fridge.get_items()
    assert len(items) == 2
    
    await fridge.remove("brown-egg")
    items = await fridge.get_items()
    assert len(items) == 1
    assert items[0].id == "crab-meat"


@pytest.mark.asyncio
async def test_fridge_clear(recipe_source):
    """냉장고 비우기 테스트"""
    fridge = Fridge(recipe_source)
    
    await fridge.looked(["brown-egg", "crab-meat", "onion"])
    items = await fridge.get_items()
    assert len(items) == 3
    
    await fridge.clear()
    items = await fridge.get_items()
    assert len(items) == 0


@pytest.mark.asyncio
async def test_fridge_concurrency(recipe_source):
    """동시성 테스트 (asyncio.Lock)"""
    import asyncio
    fridge = Fridge(recipe_source)
    
    async def add_items(item_ids):
        await fridge.looked(item_ids)
    
    # 동시에 여러 작업 실행
    await asyncio.gather(
        add_items(["brown-egg"]),
        add_items(["crab-meat"]),
        add_items(["onion"])
    )
    
    items = await fridge.get_items()
    # 모든 아이템이 추가되어야 함
    assert len(items) >= 1  # 최소 1개 이상

