from abc import ABC
from uuid import UUID
from datetime import datetime
from ..entities.reminder import Reminder


class IReminderRepository(ABC):
    """Abstract interface for reminder repository"""
    
    async def get_by_session(
        self, 
        session_id: UUID, 
        date_range_start: datetime | None = None,
        date_range_end: datetime | None = None
    ) -> list[Reminder]:
        """Get reminders by session ID with optional date range"""
        raise NotImplementedError
    
    async def save(self, reminder: Reminder) -> None:
        """Save reminder"""
        raise NotImplementedError
    
    async def update(self, reminder: Reminder) -> None:
        """Update existing reminder"""
        raise NotImplementedError
    
    async def delete(self, reminder_id: UUID) -> None:
        """Delete reminder by ID"""
        raise NotImplementedError