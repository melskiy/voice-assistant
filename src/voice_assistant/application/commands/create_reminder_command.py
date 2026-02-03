from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from voice_assistant.application.commands.base_command import BaseCommand


class CreateReminderCommand(BaseModel, BaseCommand):
    """Command to create a reminder"""
    session_id: UUID
    description: str
    reminder_date: datetime
    location: str | None = None
    repeat_interval: str | None = None  # daily, weekly, monthly