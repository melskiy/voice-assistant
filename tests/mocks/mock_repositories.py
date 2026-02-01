"""
Mock repositories for testing.

These mock implementations are used for testing and demonstration.
In production, use real repository implementations.
"""
from uuid import UUID
from typing import List

from voice_assistant.domain.entities.session import Session
from voice_assistant.domain.entities.shopping_list import ShoppingList
from voice_assistant.domain.entities.reminder import Reminder
from voice_assistant.domain.repositories.session_repository import ISessionRepository
from voice_assistant.domain.repositories.shopping_repository import IShoppingRepository
from voice_assistant.domain.repositories.reminder_repository import IReminderRepository


class MockSessionRepository(ISessionRepository):
    """Mock implementation of ISessionRepository for testing."""
    
    def __init__(self):
        self._sessions: dict[UUID, Session] = {}
    
    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    async def save(self, session: Session) -> None:
        """Save session."""
        self._sessions[session.id] = session
    
    async def update(self, session: Session) -> None:
        """Update session."""
        self._sessions[session.id] = session
    
    async def delete(self, session_id: UUID) -> None:
        """Delete session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        self._sessions.clear()


class MockShoppingRepository(IShoppingRepository):
    """Mock implementation of IShoppingRepository for testing."""
    
    def __init__(self):
        self._lists: dict[UUID, ShoppingList] = {}
    
    async def get_by_session(self, session_id: UUID) -> ShoppingList | None:
        """Get shopping list by session ID."""
        return self._lists.get(session_id)
    
    async def save(self, shopping_list: ShoppingList) -> None:
        """Save shopping list."""
        self._lists[shopping_list.session_id] = shopping_list
    
    async def update(self, shopping_list: ShoppingList) -> None:
        """Update shopping list."""
        self._lists[shopping_list.session_id] = shopping_list
    
    async def delete(self, session_id: UUID) -> None:
        """Delete shopping list."""
        if session_id in self._lists:
            del self._lists[session_id]
    
    def clear(self) -> None:
        """Clear all lists (for testing)."""
        self._lists.clear()


class MockReminderRepository(IReminderRepository):
    """Mock implementation of IReminderRepository for testing."""
    
    def __init__(self):
        self._reminders: dict[UUID, Reminder] = {}
    
    async def get_by_session(
        self, 
        session_id: UUID, 
        date_range_start=None, 
        date_range_end=None
    ) -> List[Reminder]:
        """Get reminders by session ID."""
        reminders = [
            r for r in self._reminders.values()
            if r.session_id == session_id
        ]
        
        # Filter by date range if provided
        if date_range_start:
            reminders = [r for r in reminders if r.reminder_date >= date_range_start]
        if date_range_end:
            reminders = [r for r in reminders if r.reminder_date <= date_range_end]
        
        return reminders
    
    async def save(self, reminder: Reminder) -> None:
        """Save reminder."""
        self._reminders[reminder.id] = reminder
    
    async def update(self, reminder: Reminder) -> None:
        """Update reminder."""
        self._reminders[reminder.id] = reminder
    
    async def delete(self, reminder_id: UUID) -> None:
        """Delete reminder."""
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
    
    def clear(self) -> None:
        """Clear all reminders (for testing)."""
        self._reminders.clear()
