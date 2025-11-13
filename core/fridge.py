"""
Fridge Management
Complete port of Go's ybcore/fridge.go
"""
import asyncio
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel


class FridgeItem(BaseModel):
    """
    냉장고 아이템
    Equivalent to Go's FridgeItem struct
    """
    id: str
    name: str
    quantity: int


class Fridge:
    """
    Fridge Management 클래스
    Equivalent to Go's Fridge struct한 동작
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
        냉장고를 보고 아이템 Update
        Complete port of Go's Looked 함수
        
        Args:
            item_ids: 감지된 아이템 ID list
        
        Returns:
            (아이템 list, 변경 여부)
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
            
            # 아이템 list Returns
            items = list(self._items.values())
        
        return items, changed
    
    async def get_items(self) -> List[FridgeItem]:
        """
        현재 냉장고 아이템 Get/Retrieve
        Same as Go's GetItems function
        
        Returns:
            아이템 list
        """
        async with self._lock:
            items = list(self._items.values())
        return items
    
    async def remove(self, item_id: str):
        """
        아이템 Remove
        Same as Go's Remove function
        
        Args:
            item_id: Remove할 아이템 ID
        """
        async with self._lock:
            if item_id in self._items:
                del self._items[item_id]
    
    async def clear(self):
        """
        냉장고 비우기
        Same as Go's Clear function
        """
        async with self._lock:
            self._items = {}

