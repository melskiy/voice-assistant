from pydantic import BaseModel
from uuid import UUID
from voice_assistant.application.commands.base_command import BaseCommand


class AddShoppingItemCommand(BaseModel, BaseCommand):
    """Command to add an item to a shopping list"""
    session_id: UUID
    item_name: str
    quantity: int = 1
    unit: str | None = None
    priority: str = "normal"  # low, normal, high