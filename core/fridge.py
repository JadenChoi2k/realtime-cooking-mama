"""
냉장고 관리
Go의 ybcore/fridge.go 완벽 복제
"""
import asyncio
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel


class FridgeItem(BaseModel):
    """
    냉장고 아이템
    Go의 FridgeItem 구조체와 동일
    """
    id: str
    name: str
    quantity: int


class Fridge:
    """
    냉장고 관리 클래스
    Go의 Fridge 구조체와 동일한 동작
    """
    
    def __init__(self, recipe_source):
        """
        Args:
            recipe_source: RecipeSource 인스턴스
        """
        self._items: Dict[str, FridgeItem] = {}
        self._lock = asyncio.Lock()
        self.recipe_source = recipe_source
    
    async def looked(self, item_ids: List[str]) -> Tuple[List[FridgeItem], bool]:
        """
        냉장고를 보고 아이템 업데이트
        Go의 Looked 함수 완벽 복제
        
        Args:
            item_ids: 감지된 아이템 ID 리스트
        
        Returns:
            (아이템 리스트, 변경 여부)
        """
        # 주어진 아이템의 수량 카운트
        given_item_quantity_map: Dict[str, int] = {}
        for item_id in item_ids:
            given_item_quantity_map[item_id] = given_item_quantity_map.get(item_id, 0) + 1
        
        changed = False
        
        async with self._lock:
            for item_id, quantity in given_item_quantity_map.items():
                current_item = self._items.get(item_id)
                
                if current_item is None:
                    # 새 아이템
                    changed = True
                    name = item_id
                    ingredient = self.recipe_source.get_ingredient_by_id(item_id)
                    if ingredient is not None:
                        name = ingredient.name
                    self._items[item_id] = FridgeItem(id=item_id, name=name, quantity=quantity)
                
                elif current_item.quantity < quantity:
                    # 수량 증가
                    changed = True
                    name = item_id
                    ingredient = self.recipe_source.get_ingredient_by_id(item_id)
                    if ingredient is not None:
                        name = ingredient.name
                    self._items[item_id] = FridgeItem(id=item_id, name=name, quantity=quantity)
            
            # 아이템 리스트 반환
            items = list(self._items.values())
        
        return items, changed
    
    async def get_items(self) -> List[FridgeItem]:
        """
        현재 냉장고 아이템 조회
        Go의 GetItems 함수와 동일
        
        Returns:
            아이템 리스트
        """
        async with self._lock:
            items = list(self._items.values())
        return items
    
    async def remove(self, item_id: str):
        """
        아이템 제거
        Go의 Remove 함수와 동일
        
        Args:
            item_id: 제거할 아이템 ID
        """
        async with self._lock:
            if item_id in self._items:
                del self._items[item_id]
    
    async def clear(self):
        """
        냉장고 비우기
        Go의 Clear 함수와 동일
        """
        async with self._lock:
            self._items = {}

