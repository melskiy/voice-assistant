"""
Pydantic schemas for session management endpoints.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from voice_assistant.domain.entities.call_session import SessionState


class StartCallRequest(BaseModel):
    """Request to start a new call session"""
    caller_id: str = Field(..., min_length=1, description="Caller ID (phone number)")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata for the session"
    )
    source: str = Field("api", description="Source of the call (api, freeswitch, etc.)")


class EndCallRequest(BaseModel):
    """Request to end a call session"""
    session_id: str = Field(..., description="Session ID to terminate")
    reason: Optional[str] = Field(None, description="Reason for ending the call")
    hangup_cause: str = Field("NORMAL_CLEARING", description="Hangup cause code")


class SessionResponse(BaseModel):
    """Basic session response"""
    session_id: str = Field(..., description="Unique session ID")
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Human-readable message")
    state: Optional[str] = Field(None, description="Current session state")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SessionInfo(BaseModel):
    """Detailed session information"""
    session_id: str = Field(..., description="Session ID")
    caller_id: str = Field(..., description="Caller ID")
    state: str = Field(..., description="Current state")
    is_active: bool = Field(..., description="Whether session is active")
    duration_seconds: Optional[float] = Field(None, description="Session duration in seconds")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class SessionStatusResponse(BaseModel):
    """Session status response"""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status (active/inactive)")
    message: str = Field(..., description="Status message")
    state: str = Field(..., description="Current session state")
    session_info: Optional[SessionInfo] = Field(None, description="Detailed session info")


class SessionListResponse(BaseModel):
    """List of sessions response"""
    sessions: List[SessionInfo] = Field(default_factory=list, description="List of sessions")
    total_count: int = Field(0, ge=0, description="Total number of sessions")
    active_count: int = Field(0, ge=0, description="Number of active sessions")


class CleanupResponse(BaseModel):
    """Session cleanup response"""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Result message")
    expired_count: int = Field(0, ge=0, description="Number of expired sessions cleaned up")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Cleanup timestamp")


class SessionStateUpdateRequest(BaseModel):
    """Request to update session state"""
    new_state: str = Field(..., description="New session state")
    metadata_updates: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata fields to update"
    )