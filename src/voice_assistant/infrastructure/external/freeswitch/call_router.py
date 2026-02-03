"""
Call Routing and Session Management for FreeSWITCH integration.
Handles call routing logic, session lifecycle, and integration with Gateway Service.

Offline capability: yes
CPU load: ~2-3%
Memory usage: ~10-20 MB base + ~5 MB per active session
"""
import logging
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from voice_assistant.infrastructure.external.freeswitch.mod_python_handler import (
    CallSession, CallDirection, CallEventType, FreeSWITCHSession
)
from voice_assistant.infrastructure.external.freeswitch.rtp_streamer import RTPStreamManager, RTPStreamHandler

logger = logging.getLogger(__name__)


class CallRouteType(str, Enum):
    """Types of call routing"""
    DIRECT = "direct"  # Direct to voice assistant
    QUEUE = "queue"    # Queue-based routing
    IVR = "ivr"        # IVR menu first
    TRANSFER = "transfer"  # Transfer to another destination
    REJECT = "reject"  # Reject the call


class CallPriority(int, Enum):
    """Call priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class RoutingRule:
    """Call routing rule configuration"""
    name: str
    route_type: CallRouteType
    condition: Dict[str, Any] = field(default_factory=dict)
    destination: Optional[str] = None
    priority: CallPriority = CallPriority.NORMAL
    greeting_message: Optional[str] = None
    max_duration_minutes: int = 30
    enabled: bool = True


@dataclass
class SessionContext:
    """Extended session context with routing information"""
    session: CallSession
    fs_session: Optional[FreeSWITCHSession] = None
    rtp_stream: Optional[RTPStreamHandler] = None
    route_type: CallRouteType = CallRouteType.DIRECT
    routing_rule: Optional[RoutingRule] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity"""
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.utcnow() - self.last_activity > timeout


class CallRouter:
    """
    Routes incoming calls based on configured rules.
    Implements call routing logic with priority and conditions.
    """
    
    def __init__(self):
        self._rules: List[RoutingRule] = []
        self._default_rule: Optional[RoutingRule] = None
        self._lock = threading.Lock()
    
    def add_rule(self, rule: RoutingRule) -> bool:
        """Add a routing rule"""
        with self._lock:
            # Check for duplicate names
            if any(r.name == rule.name for r in self._rules):
                logger.warning(f"Routing rule '{rule.name}' already exists")
                return False
            
            self._rules.append(rule)
            # Sort by priority (highest first)
            self._rules.sort(key=lambda r: r.priority.value, reverse=True)
            
            logger.info(f"Added routing rule: {rule.name} (priority: {rule.priority.name})")
            return True
    
    def remove_rule(self, name: str) -> bool:
        """Remove a routing rule by name"""
        with self._lock:
            for i, rule in enumerate(self._rules):
                if rule.name == name:
                    del self._rules[i]
                    logger.info(f"Removed routing rule: {name}")
                    return True
            return False
    
    def set_default_rule(self, rule: RoutingRule):
        """Set the default routing rule"""
        with self._lock:
            self._default_rule = rule
            logger.info(f"Set default routing rule: {rule.name}")
    
    def route_call(self, caller_id: str, callee_id: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> Optional[RoutingRule]:
        """
        Determine routing for an incoming call.
        
        Args:
            caller_id: Caller phone number
            callee_id: Called number (DID)
            metadata: Additional call metadata
            
        Returns:
            Matching routing rule or default rule
        """
        metadata = metadata or {}
        
        with self._lock:
            # Check rules in priority order
            for rule in self._rules:
                if not rule.enabled:
                    continue
                
                if self._matches_condition(rule, caller_id, callee_id, metadata):
                    logger.info(f"Call from {caller_id} matched rule: {rule.name}")
                    return rule
            
            # Return default rule
            if self._default_rule:
                logger.info(f"Call from {caller_id} using default rule: {self._default_rule.name}")
                return self._default_rule
            
            logger.warning(f"No routing rule found for call from {caller_id}")
            return None
    
    def _matches_condition(self, rule: RoutingRule, caller_id: str, 
                          callee_id: str, metadata: Dict[str, Any]) -> bool:
        """Check if call matches routing rule condition"""
        condition = rule.condition
        
        # Check caller ID pattern
        if "caller_pattern" in condition:
            import re
            if not re.match(condition["caller_pattern"], caller_id):
                return False
        
        # Check callee ID (DID)
        if "callee_id" in condition:
            if condition["callee_id"] != callee_id:
                return False
        
        # Check time-based conditions
        if "time_range" in condition:
            now = datetime.utcnow()
            time_range = condition["time_range"]
            start_hour = time_range.get("start_hour", 0)
            end_hour = time_range.get("end_hour", 24)
            if not (start_hour <= now.hour < end_hour):
                return False
        
        # Check metadata conditions
        if "metadata" in condition:
            for key, value in condition["metadata"].items():
                if metadata.get(key) != value:
                    return False
        
        return True
    
    def get_rules(self) -> List[RoutingRule]:
        """Get all routing rules"""
        with self._lock:
            return list(self._rules)


class SessionManager:
    """
    Manages call session lifecycle and state.
    Coordinates between FreeSWITCH, RTP streams, and Gateway Service.
    """
    
    def __init__(
        self,
        gateway_client: Optional[Any] = None,
        rtp_manager: Optional[RTPStreamManager] = None,
        session_timeout_minutes: int = 30
    ):
        self.gateway_client = gateway_client
        self.rtp_manager = rtp_manager or RTPStreamManager(gateway_client)
        self.session_timeout_minutes = session_timeout_minutes
        
        # Session storage
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = threading.Lock()
        
        # Callbacks
        self.on_session_created: Optional[Callable[[SessionContext], None]] = None
        self.on_session_ended: Optional[Callable[[SessionContext], None]] = None
        self.on_session_expired: Optional[Callable[[SessionContext], None]] = None
        
        # Cleanup thread
        self._cleanup_running = False
        self._cleanup_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start session manager"""
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Session manager started")
    
    def stop(self):
        """Stop session manager"""
        self._cleanup_running = False
        
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        
        # End all active sessions
        with self._lock:
            sessions = list(self._sessions.values())
        
        for context in sessions:
            self.end_session(context.session.session_id)
        
        # Stop RTP manager
        self.rtp_manager.stop_all()
        
        logger.info("Session manager stopped")
    
    def create_session(
        self,
        caller_id: str,
        callee_id: str,
        fs_session: FreeSWITCHSession,
        route_type: CallRouteType = CallRouteType.DIRECT,
        routing_rule: Optional[RoutingRule] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionContext]:
        """
        Create a new call session.
        
        Args:
            caller_id: Caller phone number
            callee_id: Called number
            fs_session: FreeSWITCH session wrapper
            route_type: Routing type for this call
            routing_rule: Matched routing rule
            metadata: Additional metadata
            
        Returns:
            Session context or None on failure
        """
        try:
            session_id = fs_session.session_id
            
            with self._lock:
                if session_id in self._sessions:
                    logger.warning(f"Session {session_id} already exists")
                    return self._sessions[session_id]
                
                # Create call session
                call_session = CallSession(
                    session_id=session_id,
                    caller_id=caller_id,
                    callee_id=callee_id,
                    direction=CallDirection.INBOUND,
                    metadata=metadata or {}
                )
                
                # Create session context
                context = SessionContext(
                    session=call_session,
                    fs_session=fs_session,
                    route_type=route_type,
                    routing_rule=routing_rule,
                    metadata=metadata or {}
                )
                
                self._sessions[session_id] = context
            
            # Register with Gateway Service
            if self.gateway_client:
                gateway_session_id = self.gateway_client.start_call(
                    caller_id=caller_id,
                    metadata={
                        **(metadata or {}),
                        "fs_session_id": session_id,
                        "route_type": route_type.value,
                        "rule_name": routing_rule.name if routing_rule else None
                    }
                )
                
                if gateway_session_id:
                    context.session.metadata["gateway_session_id"] = gateway_session_id
                    logger.info(f"Registered session {session_id} with Gateway Service")
                else:
                    logger.warning(f"Failed to register session {session_id} with Gateway Service")
            
            # Trigger callback
            if self.on_session_created:
                self.on_session_created(context)
            
            logger.info(f"Created session {session_id} for caller {caller_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            return None
    
    def setup_rtp_stream(
        self,
        session_id: str,
        local_port: int = 0,
        remote_host: str = "",
        remote_port: int = 0,
        payload_type: int = 0
    ) -> bool:
        """Setup RTP stream for a session"""
        try:
            with self._lock:
                if session_id not in self._sessions:
                    logger.error(f"Session {session_id} not found")
                    return False
                
                context = self._sessions[session_id]
            
            # Create RTP stream
            stream = self.rtp_manager.create_stream(
                session_id=session_id,
                local_port=local_port,
                remote_host=remote_host,
                remote_port=remote_port,
                payload_type=payload_type
            )
            
            if not stream:
                logger.error(f"Failed to create RTP stream for session {session_id}")
                return False
            
            # Start the stream
            if not self.rtp_manager.start_stream(session_id):
                logger.error(f"Failed to start RTP stream for session {session_id}")
                return False
            
            # Update context
            context.rtp_stream = stream
            context.touch()
            
            logger.info(f"Setup RTP stream for session {session_id} on port {stream.local_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up RTP stream: {e}")
            return False
    
    def end_session(self, session_id: str, reason: str = "normal") -> bool:
        """End a call session"""
        try:
            with self._lock:
                if session_id not in self._sessions:
                    return False
                
                context = self._sessions[session_id]
                context.session.is_active = False
                context.session.end_time = datetime.utcnow()
            
            # Stop RTP stream
            self.rtp_manager.stop_stream(session_id)
            
            # Notify Gateway Service
            gateway_session_id = context.session.metadata.get("gateway_session_id")
            if gateway_session_id and self.gateway_client:
                self.gateway_client.end_call(gateway_session_id)
            
            # Hangup FreeSWITCH session
            if context.fs_session:
                context.fs_session.hangup(reason)
            
            # Trigger callback
            if self.on_session_ended:
                self.on_session_ended(context)
            
            # Remove from storage
            with self._lock:
                if session_id in self._sessions:
                    del self._sessions[session_id]
            
            logger.info(f"Ended session {session_id}, reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get session context by ID"""
        with self._lock:
            context = self._sessions.get(session_id)
            if context:
                context.touch()
            return context
    
    def get_session_by_caller(self, caller_id: str) -> Optional[SessionContext]:
        """Get session by caller ID"""
        with self._lock:
            for context in self._sessions.values():
                if context.session.caller_id == caller_id:
                    context.touch()
                    return context
            return None
    
    def get_all_sessions(self) -> Dict[str, SessionContext]:
        """Get all active sessions"""
        with self._lock:
            return dict(self._sessions)
    
    def update_session_metadata(self, session_id: str, 
                               metadata_updates: Dict[str, Any]) -> bool:
        """Update session metadata"""
        try:
            with self._lock:
                if session_id not in self._sessions:
                    return False
                
                context = self._sessions[session_id]
                context.session.metadata.update(metadata_updates)
                context.metadata.update(metadata_updates)
                context.touch()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session metadata: {e}")
            return False
    
    def play_greeting(self, session_id: str, greeting_message: Optional[str] = None) -> bool:
        """Play greeting message for a session"""
        try:
            context = self.get_session(session_id)
            if not context or not context.fs_session:
                return False
            
            # Use rule-specific greeting or default
            message = greeting_message
            if not message and context.routing_rule:
                message = context.routing_rule.greeting_message
            if not message:
                message = "Здравствуйте! Я голосовой помощник. Чем могу помочь?"
            
            # Play via TTS
            success = context.fs_session.speak_tts(message)
            
            if success:
                context.touch()
                logger.info(f"Played greeting for session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error playing greeting: {e}")
            return False
    
    def play_response(self, session_id: str, text: str) -> bool:
        """Play TTS response for a session"""
        try:
            context = self.get_session(session_id)
            if not context or not context.fs_session:
                return False
            
            success = context.fs_session.speak_tts(text)
            
            if success:
                context.touch()
                logger.debug(f"Played response for session {session_id}: {text[:50]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"Error playing response: {e}")
            return False
    
    def handle_dtmf(self, session_id: str, digit: str) -> bool:
        """Handle DTMF input for a session"""
        try:
            context = self.get_session(session_id)
            if not context:
                return False
            
            # Append to DTMF buffer
            context.session.dtmf_buffer += digit
            context.touch()
            
            # Send to Gateway Service
            gateway_session_id = context.session.metadata.get("gateway_session_id")
            if gateway_session_id and self.gateway_client:
                self.gateway_client.send_dtmf(gateway_session_id, digit)
            
            logger.debug(f"Handled DTMF '{digit}' for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling DTMF: {e}")
            return False
    
    def _cleanup_loop(self):
        """Background thread for cleaning up expired sessions"""
        import time
        
        while self._cleanup_running:
            try:
                time.sleep(60)  # Check every minute
                
                expired_sessions = []
                
                with self._lock:
                    for session_id, context in self._sessions.items():
                        if context.is_expired(self.session_timeout_minutes):
                            expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    logger.warning(f"Session {session_id} expired due to inactivity")
                    
                    context = self.get_session(session_id)
                    if context and self.on_session_expired:
                        self.on_session_expired(context)
                    
                    self.end_session(session_id, reason="SESSION_TIMEOUT")
                    
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        with self._lock:
            total_sessions = len(self._sessions)
            active_sessions = sum(1 for c in self._sessions.values() if c.session.is_active)
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "rtp_streams": len(self.rtp_manager.get_all_streams()),
                "session_timeout_minutes": self.session_timeout_minutes
            }


class CallFlowOrchestrator:
    """
    Orchestrates the complete call flow from incoming call to completion.
    Integrates CallRouter, SessionManager, and Gateway Service.
    """
    
    def __init__(
        self,
        gateway_client: Optional[Any] = None,
        session_timeout_minutes: int = 30
    ):
        self.gateway_client = gateway_client
        self.call_router = CallRouter()
        self.session_manager = SessionManager(
            gateway_client=gateway_client,
            session_timeout_minutes=session_timeout_minutes
        )
        
        # Setup default routing
        self._setup_default_routing()
        
        # Setup session callbacks
        self.session_manager.on_session_created = self._on_session_created
        self.session_manager.on_session_ended = self._on_session_ended
    
    def _setup_default_routing(self):
        """Setup default routing rules"""
        default_rule = RoutingRule(
            name="default",
            route_type=CallRouteType.DIRECT,
            greeting_message="Здравствуйте! Я голосовой помощник. Чем могу помочь?",
            priority=CallPriority.LOW
        )
        self.call_router.set_default_rule(default_rule)
    
    def start(self):
        """Start the orchestrator"""
        self.session_manager.start()
        logger.info("Call flow orchestrator started")
    
    def stop(self):
        """Stop the orchestrator"""
        self.session_manager.stop()
        logger.info("Call flow orchestrator stopped")
    
    def handle_incoming_call(self, fs_session: FreeSWITCHSession, 
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle an incoming call through the complete flow.
        
        Args:
            fs_session: FreeSWITCH session wrapper
            metadata: Additional call metadata
            
        Returns:
            True if call was handled successfully
        """
        try:
            caller_id = fs_session.caller_id
            callee_id = fs_session.callee_id
            
            # Determine routing
            routing_rule = self.call_router.route_call(caller_id, callee_id, metadata)
            
            if not routing_rule:
                logger.warning(f"No routing rule for call from {caller_id}")
                fs_session.hangup("CALL_REJECTED")
                return False
            
            # Handle based on route type
            if routing_rule.route_type == CallRouteType.REJECT:
                logger.info(f"Rejecting call from {caller_id} per rule {routing_rule.name}")
                fs_session.hangup("CALL_REJECTED")
                return False
            
            # Answer the call
            if not fs_session.answer():
                logger.error(f"Failed to answer call from {caller_id}")
                return False
            
            # Create session
            context = self.session_manager.create_session(
                caller_id=caller_id,
                callee_id=callee_id,
                fs_session=fs_session,
                route_type=routing_rule.route_type,
                routing_rule=routing_rule,
                metadata=metadata
            )
            
            if not context:
                logger.error(f"Failed to create session for call from {caller_id}")
                fs_session.hangup("NORMAL_TEMPORARY_FAILURE")
                return False
            
            # Play greeting
            self.session_manager.play_greeting(context.session.session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}", exc_info=True)
            return False
    
    def _on_session_created(self, context: SessionContext):
        """Callback when session is created"""
        logger.info(f"Session created: {context.session.session_id}")
    
    def _on_session_ended(self, context: SessionContext):
        """Callback when session ends"""
        duration = 0
        if context.session.end_time and context.session.start_time:
            duration = (context.session.end_time - context.session.start_time).total_seconds()
        
        logger.info(f"Session ended: {context.session.session_id}, duration: {duration:.1f}s")
    
    def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add a routing rule"""
        return self.call_router.add_rule(rule)
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get session by ID"""
        return self.session_manager.get_session(session_id)
    
    def end_call(self, session_id: str, reason: str = "normal") -> bool:
        """End a call"""
        return self.session_manager.end_session(session_id, reason)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "routing_rules": len(self.call_router.get_rules()),
            **self.session_manager.get_stats()
        }
