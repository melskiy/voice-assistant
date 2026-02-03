from pydantic import BaseModel
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime


class Reminder(BaseModel):
    """Domain entity representing a reminder"""
    id: UUID
    session_id: UUID
    description: str
    reminder_date: datetime
    location: str | None = None
    repeat_interval: str | None = None  # daily, weekly, monthly, none
    created_at: datetime = datetime.utcnow()
    notified: bool = False

    class Config:
        arbitrary_types_allowed = True

    def is_overdue(self) -> bool:
        """Check if the reminder is overdue"""
        return datetime.utcnow() > self.reminder_date and not self.notified

    def is_upcoming(self, within_minutes: int = 60) -> bool:
        """Check if the reminder is upcoming within specified minutes"""
        time_until_reminder = self.reminder_date - datetime.utcnow()
        return 0 < time_until_reminder.total_seconds() <= (within_minutes * 60)

    def mark_as_notified(self) -> None:
        """Mark the reminder as notified"""
        self.notified = True

    def should_repeat(self) -> bool:
        """Check if the reminder should be repeated"""
        return self.repeat_interval is not None and self.repeat_interval != "none"

    @classmethod
    def create(
        cls,
        session_id: UUID,
        description: str,
        reminder_date: datetime,
        location: str | None = None,
        repeat_interval: str | None = None
    ) -> 'Reminder':
        """Factory method to create a reminder"""
        return cls(
            id=uuid4(),
            session_id=session_id,
            description=description,
            reminder_date=reminder_date,
            location=location,
            repeat_interval=repeat_interval
        )

    def __str__(self) -> str:
        return f"Reminder: {self.description} at {self.reminder_date.strftime('%Y-%m-%d %H:%M')}"