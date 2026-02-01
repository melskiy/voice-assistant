"""
Pydantic schemas for reminder endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID


class ReminderCreateRequest(BaseModel):
    """Request to create a reminder"""
    description: str = Field(..., min_length=1, max_length=500, description="Reminder description")
    reminder_date: datetime = Field(..., description="When the reminder should trigger")
    location: Optional[str] = Field(None, max_length=255, description="Optional location")
    repeat_interval: Optional[str] = Field(None, description="Repeat interval (daily, weekly, monthly, none)")

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate and clean description"""
        cleaned = v.strip()
        if len(cleaned) < 1:
            raise ValueError("Description cannot be empty")
        return cleaned

    @field_validator('repeat_interval')
    @classmethod
    def validate_repeat_interval(cls, v: Optional[str]) -> Optional[str]:
        """Validate repeat interval"""
        if v is None:
            return None
        valid_intervals = {'daily', 'weekly', 'monthly', 'none'}
        if v.lower() not in valid_intervals:
            raise ValueError(f"Repeat interval must be one of: {valid_intervals}")
        return v.lower()

    @field_validator('reminder_date')
    @classmethod
    def validate_reminder_date(cls, v: datetime) -> datetime:
        """Validate reminder date is not in the past by too much"""
        # Allow some flexibility for timezone differences
        now = datetime.utcnow()
        if v < now.replace(hour=0, minute=0, second=0, microsecond=0):
            # Check if it's more than 1 day in the past
            if (now - v).days > 1:
                raise ValueError("Reminder date cannot be more than 1 day in the past")
        return v


class ReminderUpdateRequest(BaseModel):
    """Request to update a reminder"""
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="Reminder description")
    reminder_date: Optional[datetime] = Field(None, description="When the reminder should trigger")
    location: Optional[str] = Field(None, max_length=255, description="Optional location")
    repeat_interval: Optional[str] = Field(None, description="Repeat interval")
    notified: Optional[bool] = Field(None, description="Whether reminder has been notified")

    @field_validator('repeat_interval')
    @classmethod
    def validate_repeat_interval(cls, v: Optional[str]) -> Optional[str]:
        """Validate repeat interval"""
        if v is None:
            return None
        valid_intervals = {'daily', 'weekly', 'monthly', 'none'}
        if v.lower() not in valid_intervals:
            raise ValueError(f"Repeat interval must be one of: {valid_intervals}")
        return v.lower()


class ReminderResponse(BaseModel):
    """Reminder response"""
    id: str = Field(..., description="Reminder ID")
    session_id: str = Field(..., description="Session ID")
    description: str = Field(..., description="Reminder description")
    reminder_date: datetime = Field(..., description="When the reminder triggers")
    location: Optional[str] = Field(None, description="Location")
    repeat_interval: Optional[str] = Field(None, description="Repeat interval")
    created_at: datetime = Field(..., description="When reminder was created")
    notified: bool = Field(False, description="Whether reminder has been notified")
    is_overdue: bool = Field(False, description="Whether reminder is overdue")
    is_upcoming: bool = Field(False, description="Whether reminder is upcoming (within 1 hour)")

    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    """List of reminders response"""
    session_id: str = Field(..., description="Session ID")
    reminders: list[ReminderResponse] = Field(default_factory=list, description="List of reminders")
    total_count: int = Field(0, ge=0, description="Total number of reminders")
    overdue_count: int = Field(0, ge=0, description="Number of overdue reminders")
    upcoming_count: int = Field(0, ge=0, description="Number of upcoming reminders")


class ReminderDeleteResponse(BaseModel):
    """Reminder deletion response"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Result message")
    deleted_reminder_id: Optional[str] = Field(None, description="ID of deleted reminder")