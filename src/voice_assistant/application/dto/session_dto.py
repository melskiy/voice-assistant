from pydantic import BaseModel
from typing import Any
from uuid import UUID
from datetime import datetime
from voice_assistant.domain.entities.session import DialogState


class SessionDTO(BaseModel):
    """Data transfer object for session data"""
    session_id: UUID
    phone_number: str
    current_state: DialogState
    context_data: dict[str, Any]
    created_at: datetime
    last_activity: datetime

    @classmethod
    def from_entity(cls, session) -> 'SessionDTO':
        """Create DTO from domain entity"""
        return cls(
            session_id=session.id,
            phone_number=session.phone_number.number,
            current_state=session.state,
            context_data=session.context_data,
            created_at=session.created_at,
            last_activity=session.last_activity
        )

    def to_entity(self):
        """Convert DTO back to domain entity (partial conversion)"""
        from voice_assistant.domain.value_objects.phone_number import PhoneNumber
        return {
            'id': self.session_id,
            'phone_number': PhoneNumber(number=self.phone_number),
            'state': self.current_state,
            'context_data': self.context_data,
            'created_at': self.created_at,
            'last_activity': self.last_activity
        }