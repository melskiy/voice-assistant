from abc import ABC
from typing import Optional
from uuid import UUID
from ..entities.shopping_list import ShoppingList


class IShoppingRepository(ABC):
    """Abstract interface for shopping list repository"""
    
    async def get_by_session(self, session_id: UUID) -> ShoppingList | None:
        """Get shopping list by session ID"""
        raise NotImplementedError
    
    async def save(self, shopping_list: ShoppingList) -> None:
        """Save shopping list"""
        raise NotImplementedError
    
    async def update(self, shopping_list: ShoppingList) -> None:
        """Update existing shopping list"""
        raise NotImplementedError
    
    async def delete(self, session_id: UUID) -> None:
        """Delete shopping list by session ID"""
        raise NotImplementedError