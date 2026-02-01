"""
Pydantic schemas for Gateway Service API.
Provides type-safe request/response models for all endpoints.
"""

from .audio_schemas import (
    AudioChunkRequest,
    ProcessAudioRequest,
    AudioProcessingResponse,
    AudioStatsResponse,
    ASRResult,
)
from .session_schemas import (
    StartCallRequest,
    EndCallRequest,
    SessionResponse,
    SessionStatusResponse,
    SessionListResponse,
    CleanupResponse,
    SessionInfo,
    SessionStateUpdateRequest,
)
from .freeswitch_schemas import (
    DTMFRequest,
    RTPStreamRequest,
    RTPStreamResponse,
    GreetingRequest,
    CallControlResponse,
    FreeSwitchSessionResponse,
    FreeSwitchStatsResponse,
    ActiveSessionInfo,
)
from .shopping_schemas import (
    ShoppingItemCreateRequest,
    ShoppingItemResponse,
    ShoppingListResponse,
    ShoppingItemUpdateRequest,
    ShoppingItemDeleteResponse,
)
from .reminder_schemas import (
    ReminderCreateRequest,
    ReminderResponse,
    ReminderListResponse,
    ReminderUpdateRequest,
    ReminderDeleteResponse,
)
from .common_schemas import (
    HealthResponse,
    ErrorResponse,
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # Audio schemas
    "AudioChunkRequest",
    "ProcessAudioRequest",
    "AudioProcessingResponse",
    "AudioStatsResponse",
    "ASRResult",
    # Session schemas
    "StartCallRequest",
    "EndCallRequest",
    "SessionResponse",
    "SessionStatusResponse",
    "SessionListResponse",
    "CleanupResponse",
    "SessionInfo",
    "SessionStateUpdateRequest",
    # FreeSwitch schemas
    "DTMFRequest",
    "RTPStreamRequest",
    "RTPStreamResponse",
    "GreetingRequest",
    "CallControlResponse",
    "FreeSwitchSessionResponse",
    "FreeSwitchStatsResponse",
    "ActiveSessionInfo",
    # Shopping schemas
    "ShoppingItemCreateRequest",
    "ShoppingItemResponse",
    "ShoppingListResponse",
    "ShoppingItemUpdateRequest",
    "ShoppingItemDeleteResponse",
    # Reminder schemas
    "ReminderCreateRequest",
    "ReminderResponse",
    "ReminderListResponse",
    "ReminderUpdateRequest",
    "ReminderDeleteResponse",
    # Common schemas
    "HealthResponse",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
]