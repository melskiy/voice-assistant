"""
Pydantic schemas for FreeSWITCH integration endpoints.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class DTMFRequest(BaseModel):
    """DTMF (touch-tone) event request from FreeSWITCH"""
    session_id: str = Field(..., description="Session ID")
    digit: str = Field(..., min_length=1, max_length=1, description="DTMF digit (0-9, *, #)")
    duration_ms: int = Field(100, ge=50, le=5000, description="DTMF tone duration in milliseconds")

    @field_validator('digit')
    @classmethod
    def validate_digit(cls, v: str) -> str:
        """Validate DTMF digit"""
        valid_digits = set('0123456789*#')
        if v not in valid_digits:
            raise ValueError(f"Invalid DTMF digit: {v}. Must be one of {valid_digits}")
        return v


class RTPStreamRequest(BaseModel):
    """RTP stream setup request"""
    session_id: str = Field(..., description="Session ID")
    local_port: int = Field(0, ge=0, le=65535, description="Local RTP port")
    remote_host: str = Field("", description="Remote RTP host")
    remote_port: int = Field(0, ge=0, le=65535, description="Remote RTP port")
    payload_type: int = Field(0, ge=0, le=127, description="RTP payload type (0=PCMU, 8=PCMA)")
    sample_rate: int = Field(8000, ge=8000, le=48000, description="Audio sample rate in Hz")


class RTPStreamResponse(BaseModel):
    """RTP stream setup response"""
    session_id: str = Field(..., description="Session ID")
    local_port: int = Field(..., description="Local RTP port")
    status: str = Field(..., description="Setup status")
    message: str = Field(..., description="Status message")


class GreetingRequest(BaseModel):
    """Greeting playback request"""
    session_id: str = Field(..., description="Session ID")
    message: Optional[str] = Field(None, description="Custom greeting message (optional)")
    use_tts: bool = Field(True, description="Whether to use TTS for greeting")
    language: str = Field("ru", description="Greeting language code")


class CallControlResponse(BaseModel):
    """Call control response"""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Response message")
    action: str = Field(..., description="Action performed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class RTPConfig(BaseModel):
    """RTP configuration details"""
    local_port: Optional[int] = Field(None, description="Local RTP port")
    remote_host: Optional[str] = Field(None, description="Remote RTP host")
    remote_port: Optional[int] = Field(None, description="Remote RTP port")
    payload_type: Optional[int] = Field(None, description="RTP payload type")
    sample_rate: Optional[int] = Field(None, description="Sample rate")
    setup_time: Optional[datetime] = Field(None, description="RTP setup timestamp")


class CallMetadata(BaseModel):
    """Call metadata information"""
    source: Optional[str] = Field(None, description="Call source")
    incoming_time: Optional[datetime] = Field(None, description="Incoming call time")
    answered_time: Optional[datetime] = Field(None, description="Call answered time")
    greeting_played: Optional[bool] = Field(None, description="Whether greeting was played")
    greeting_message: Optional[str] = Field(None, description="Greeting message text")
    greeting_time: Optional[datetime] = Field(None, description="Greeting playback time")
    last_dtmf: Optional[str] = Field(None, description="Last DTMF digit received")
    last_dtmf_time: Optional[datetime] = Field(None, description="Last DTMF time")
    last_response: Optional[str] = Field(None, description="Last response text")
    last_response_time: Optional[datetime] = Field(None, description="Last response time")
    rtp_config: Optional[RTPConfig] = Field(None, description="RTP configuration")


class FreeSwitchSessionResponse(BaseModel):
    """Detailed FreeSWITCH session response"""
    session_id: str = Field(..., description="Session ID")
    caller_id: str = Field(..., description="Caller ID")
    state: str = Field(..., description="Current session state")
    is_active: bool = Field(..., description="Whether session is active")
    duration_seconds: Optional[float] = Field(None, description="Call duration in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Full session metadata")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")


class ActiveSessionInfo(BaseModel):
    """Active session information for stats"""
    session_id: str = Field(..., description="Session ID")
    caller_id: str = Field(..., description="Caller ID")
    state: str = Field(..., description="Current state")
    duration_seconds: Optional[float] = Field(None, description="Call duration")


class FreeSwitchStatsResponse(BaseModel):
    """FreeSWITCH integration statistics"""
    status: str = Field(..., description="Response status")
    active_sessions_count: int = Field(0, ge=0, description="Number of active sessions")
    active_sessions: List[ActiveSessionInfo] = Field(
        default_factory=list,
        description="List of active sessions"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")