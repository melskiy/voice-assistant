"""
Application command and query handlers.

Handlers process commands and queries, delegating to use cases
and domain entities. Each handler has a single responsibility.
"""

from .add_shopping_item_handler import AddShoppingItemHandler
from .create_reminder_handler import CreateReminderHandler

__all__ = [
    'AddShoppingItemHandler',
    'CreateReminderHandler',
]
