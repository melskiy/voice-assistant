from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from voice_assistant.domain.value_objects.priority import Priority


class ShoppingItemDTO(BaseModel):
    """Data transfer object for shopping list items"""
    id: UUID
    name: str
    quantity: int
    unit: str | None = None
    priority: Priority = Priority.NORMAL
    added_at: datetime

    @classmethod
    def from_entity(cls, item) -> 'ShoppingItemDTO':
        """Create DTO from domain entity"""
        return cls(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            priority=item.priority,
            added_at=item.added_at
        )