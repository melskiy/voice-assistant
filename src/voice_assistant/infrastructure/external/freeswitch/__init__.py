"""
FreeSWITCH integration module for voice assistant.
Provides mod_python3 integration, RTP streaming, and call routing.

Offline capability: yes
CPU load: ~5-10% per active call
Memory usage: ~50-100 MB per active call
"""

from voice_assistant.infrastructure.external.freeswitch.mod_python_handler import (
    CallEventType,
    CallDirection,
    CallSession,
    AudioFrame,
    DTMFEvent,
    FreeSWITCHSession,
    GatewayServiceClient,
    CallEventHandler,
    FreeSWITCHCallHandler,
    handler,
    create_handler,
)

from voice_assistant.infrastructure.external.freeswitch.rtp_streamer import (
    RTPPacket,
    AudioBuffer,
    PCMDecoder,
    RTPStreamHandler,
    RTPStreamManager,
)

from voice_assistant.infrastructure.external.freeswitch.call_router import (
    CallRouteType,
    CallPriority,
    RoutingRule,
    SessionContext,
    CallRouter,
    SessionManager,
    CallFlowOrchestrator,
)

__all__ = [
    # mod_python_handler
    "CallEventType",
    "CallDirection",
    "CallSession",
    "AudioFrame",
    "DTMFEvent",
    "FreeSWITCHSession",
    "GatewayServiceClient",
    "CallEventHandler",
    "FreeSWITCHCallHandler",
    "handler",
    "create_handler",
    # rtp_streamer
    "RTPPacket",
    "AudioBuffer",
    "PCMDecoder",
    "RTPStreamHandler",
    "RTPStreamManager",
    # call_router
    "CallRouteType",
    "CallPriority",
    "RoutingRule",
    "SessionContext",
    "CallRouter",
    "SessionManager",
    "CallFlowOrchestrator",
]
