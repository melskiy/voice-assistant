from pydantic import BaseModel, Field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from datetime import datetime


class SessionState(str, Enum):
    """Enumeration of possible call session states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"


class CallSession(BaseModel):
    """Domain entity representing a FreeSWITCH call session"""
    session_id: UUID = Field(default_factory=uuid4)
    caller_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    state: SessionState = SessionState.INITIALIZING
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True

    def update_state(self, new_state: SessionState, metadata_updates: Optional[Dict[str, Any]] = None) -> None:
        """Update the session state and metadata"""
        self.state = new_state
        if metadata_updates:
            self.metadata.update(metadata_updates)

    def terminate(self) -> None:
        """Terminate the session"""
        self.state = SessionState.TERMINATED
        self.end_time = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if session is currently active"""
        return self.state in [SessionState.ACTIVE, SessionState.PROCESSING, SessionState.WAITING_FOR_INPUT]

    def is_terminated(self) -> bool:
        """Check if session has been terminated"""
        return self.state == SessionState.TERMINATED

    def get_duration(self) -> Optional[float]:
        """Get session duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()

    @classmethod
    def create(cls, caller_id: str, metadata: Optional[Dict[str, Any]] = None) -> 'CallSession':
        """Factory method to create a new call session"""
        return cls(
            caller_id=caller_id,
            metadata=metadata or {}
        )

    def can_transition_to(self, target_state: SessionState) -> bool:
        """Check if state transition is allowed"""
        valid_transitions = {
            SessionState.INITIALIZING: [SessionState.ACTIVE, SessionState.ERROR, SessionState.TERMINATED],
            SessionState.ACTIVE: [SessionState.PROCESSING, SessionState.WAITING_FOR_INPUT, SessionState.TERMINATING, SessionState.ERROR],
            SessionState.PROCESSING: [SessionState.ACTIVE, SessionState.WAITING_FOR_INPUT, SessionState.TERMINATING, SessionState.ERROR],
            SessionState.WAITING_FOR_INPUT: [SessionState.PROCESSING, SessionState.ACTIVE, SessionState.TERMINATING, SessionState.ERROR],
            SessionState.TERMINATING: [SessionState.TERMINATED],
            SessionState.ERROR: [SessionState.TERMINATING, SessionState.TERMINATED],
            SessionState.TERMINATED: []  # Terminal state
        }
        
        return target_state in valid_transitions.get(self.state, [])