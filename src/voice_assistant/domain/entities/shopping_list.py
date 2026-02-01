from pydantic import BaseModel
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from ..value_objects.priority import Priority


class ShoppingListItem(BaseModel):
    """Domain entity representing an item in a shopping list"""
    id: UUID
    name: str
    quantity: int = 1
    unit: str | None = None
    priority: Priority = Priority.NORMAL
    added_at: datetime

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def create(
        cls,
        name: str,
        quantity: int = 1,
        unit: str | None = None,
        priority: Priority = Priority.NORMAL
    ) -> 'ShoppingListItem':
        """Factory method to create a shopping list item"""
        return cls(
            id=uuid4(),
            name=name,
            quantity=quantity,
            unit=unit,
            priority=priority,
            added_at=datetime.utcnow()
        )

    def __str__(self) -> str:
        if self.unit:
            return f"{self.name} ({self.quantity} {self.unit})"
        return f"{self.name} ({self.quantity})"


class ShoppingList(BaseModel):
    """Domain entity representing a shopping list"""
    session_id: UUID
    items: list[ShoppingListItem] = []

    def add_item(self, item: ShoppingListItem) -> None:
        """Add an item to the shopping list"""
        self.items.append(item)

    def remove_item(self, item_name: str) -> bool:
        """Remove an item from the shopping list by name"""
        for i, item in enumerate(self.items):
            if item.name.lower() == item_name.lower():
                del self.items[i]
                return True
        return False

    def get_item(self, item_name: str) -> ShoppingListItem | None:
        """Get an item from the shopping list by name"""
        for item in self.items:
            if item.name.lower() == item_name.lower():
                return item
        return None

    def get_items_by_priority(self, priority: Priority) -> list[ShoppingListItem]:
        """Get items with a specific priority"""
        return [item for item in self.items if item.priority == priority]

    def total_items(self) -> int:
        """Get total number of items in the list"""
        return len(self.items)

    def total_quantity(self) -> int:
        """Get total quantity of all items"""
        return sum(item.quantity for item in self.items)

    def clear(self) -> None:
        """Clear all items from the list"""
        self.items.clear()

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)