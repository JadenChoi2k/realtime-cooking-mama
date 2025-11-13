"""
Fridge Management
Complete port of Go's ybcore/fridge.go
"""
import asyncio
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel


class FridgeItem(BaseModel):
    """
    Fridge item
    Equivalent to Go's FridgeItem struct
    """
    id: str
    name: str
    quantity: int


class Fridge:
    """
    Fridge Management class
    Equivalent to Go's Fridge struct behavior
    """
    
    def __init__(self, recipe_source):
        """
        Args:
            recipe_source: RecipeSource instance
        """
        self._items: Dict[str, FridgeItem] = {}
        self._lock = asyncio.Lock()
        self.recipe_source = recipe_source
    
    async def looked(self, item_ids: List[str]) -> Tuple[List[FridgeItem], bool]:
        """
        Look at fridge and update items
        Complete port of Go's Looked function
        
        Args:
            item_ids: Detected item ID list
        
        Returns:
            (Item list, changed flag)
        """
        # Count quantity of given items
        given_item_quantity_map: Dict[str, int] = {}
        for item_id in item_ids:
            given_item_quantity_map[item_id] = given_item_quantity_map.get(item_id, 0) + 1
        
        changed = False
        
        async with self._lock:
            for item_id, quantity in given_item_quantity_map.items():
                current_item = self._items.get(item_id)
                
                if current_item is None:
                    # New item
                    changed = True
                    name = item_id
                    ingredient = self.recipe_source.get_ingredient_by_id(item_id)
                    if ingredient is not None:
                        name = ingredient.name
                    self._items[item_id] = FridgeItem(id=item_id, name=name, quantity=quantity)
                
                elif current_item.quantity < quantity:
                    # Quantity increased
                    changed = True
                    name = item_id
                    ingredient = self.recipe_source.get_ingredient_by_id(item_id)
                    if ingredient is not None:
                        name = ingredient.name
                    self._items[item_id] = FridgeItem(id=item_id, name=name, quantity=quantity)
            
            # Return item list
            items = list(self._items.values())
        
        return items, changed
    
    async def get_items(self) -> List[FridgeItem]:
        """
        Get current fridge items
        Same as Go's GetItems function
        
        Returns:
            Item list
        """
        async with self._lock:
            items = list(self._items.values())
        return items
    
    async def remove(self, item_id: str):
        """
        Remove item
        Same as Go's Remove function
        
        Args:
            item_id: Item ID to remove
        """
        async with self._lock:
            if item_id in self._items:
                del self._items[item_id]
    
    async def clear(self):
        """
        Clear fridge
        Same as Go's Clear function
        """
        async with self._lock:
            self._items = {}
