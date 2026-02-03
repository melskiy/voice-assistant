from pydantic import BaseModel
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from datetime import datetime
from ..value_objects.phone_number import PhoneNumber


class DialogState(str, Enum):
    """Enumeration of possible dialog states"""
    AWAITING_COMMAND = "awaiting_command"
    COLLECTING_ITEM = "collecting_item"
    AWAITING_DATE = "awaiting_date"
    AWAITING_LOCATION = "awaiting_location"
    CONFIRMING = "confirming"
    ERROR_RECOVERY = "error_recovery"
    COMPLETED = "completed"


class Session(BaseModel):
    """Domain entity representing a conversation session"""
    id: UUID
    phone_number: PhoneNumber
    state: DialogState
    context_data: dict[str, Any]
    created_at: datetime
    last_activity: datetime

    class Config:
        arbitrary_types_allowed = True

    def update_state(self, new_state: DialogState, context_updates: dict[str, Any] | None = None) -> None:
        """Update the session state and context"""
        self.state = new_state
        if context_updates:
            self.context_data.update(context_updates)
        self.last_activity = datetime.utcnow()

    def reset_context(self) -> None:
        """Reset the session context data"""
        self.context_data.clear()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired based on inactivity"""
        time_since_last_activity = datetime.utcnow() - self.last_activity
        return time_since_last_activity.total_seconds() > (timeout_minutes * 60)

    @classmethod
    def create(cls, phone_number: PhoneNumber) -> 'Session':
        """Factory method to create a new session"""
        now = datetime.utcnow()
        return cls(
            id=uuid4(),
            phone_number=phone_number,
            state=DialogState.AWAITING_COMMAND,
            context_data={},
            created_at=now,
            last_activity=now
        )

    def can_transition_to(self, target_state: DialogState) -> bool:
        """Check if state transition is allowed"""
        # Define valid state transitions
        valid_transitions = {
            DialogState.AWAITING_COMMAND: [
                DialogState.COLLECTING_ITEM,
                DialogState.AWAITING_DATE,
                DialogState.AWAITING_LOCATION,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.COLLECTING_ITEM: [
                DialogState.AWAITING_COMMAND,
                DialogState.AWAITING_DATE,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.AWAITING_DATE: [
                DialogState.AWAITING_COMMAND,
                DialogState.AWAITING_LOCATION,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.AWAITING_LOCATION: [
                DialogState.AWAITING_COMMAND,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.CONFIRMING: [
                DialogState.AWAITING_COMMAND,
                DialogState.COMPLETED,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.ERROR_RECOVERY: [
                DialogState.AWAITING_COMMAND,
                DialogState.COLLECTING_ITEM,
                DialogState.AWAITING_DATE,
                DialogState.AWAITING_LOCATION,
                DialogState.CONFIRMING
            ]
        }
        
        return target_state in valid_transitions.get(self.state, [])