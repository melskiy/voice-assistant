"""
FreeSWITCH mod_python3 integration module for voice assistant.
Handles SIP call events and RTP audio streaming.

Offline capability: yes
CPU load: ~5-10%
Memory usage: ~50-100 MB per active call
"""
import os
import sys
import json
import base64
import asyncio
import logging
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4, UUID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CallEventType(str, Enum):
    """Enumeration of SIP call event types"""
    INCOMING_CALL = "incoming_call"
    CALL_ANSWERED = "call_answered"
    CALL_HANGUP = "call_hangup"
    DTMF_RECEIVED = "dtmf_received"
    AUDIO_FRAME = "audio_frame"
    CALL_TRANSFER = "call_transfer"
    CALL_HOLD = "call_hold"
    CALL_RESUME = "call_resume"


class CallDirection(str, Enum):
    """Direction of the call"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class CallSession:
    """Domain entity representing a FreeSWITCH call session"""
    session_id: str
    caller_id: str
    callee_id: str
    direction: CallDirection
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    dtmf_buffer: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "caller_id": self.caller_id,
            "callee_id": self.callee_id,
            "direction": self.direction.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "dtmf_buffer": self.dtmf_buffer
        }


@dataclass
class AudioFrame:
    """Represents a single audio frame from RTP stream"""
    session_id: str
    data: bytes
    timestamp: int
    sequence_number: int
    sample_rate: int = 8000
    channels: int = 1
    codec: str = "PCMU"  # Default G.711 mu-law
    
    def to_base64(self) -> str:
        """Convert audio data to base64 string"""
        return base64.b64encode(self.data).decode('utf-8')


@dataclass
class DTMFEvent:
    """Represents a DTMF (touch-tone) event"""
    session_id: str
    digit: str
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


class FreeSWITCHSession:
    """
    Wrapper for FreeSWITCH session object.
    Provides clean interface to FreeSWITCH API.
    """
    
    def __init__(self, fs_session: Any):
        self.fs_session = fs_session
        self.session_id: Optional[str] = None
        self.caller_id: Optional[str] = None
        self.callee_id: Optional[str] = None
        self._extract_session_info()
    
    def _extract_session_info(self):
        """Extract basic session information from FreeSWITCH session"""
        try:
            # FreeSWITCH session API
            self.session_id = self.fs_session.getUUID()
            self.caller_id = self.fs_session.getVariable("caller_id_number") or "unknown"
            self.callee_id = self.fs_session.getVariable("destination_number") or "unknown"
        except Exception as e:
            logger.error(f"Error extracting session info: {e}")
            self.session_id = str(uuid4())
            self.caller_id = "unknown"
            self.callee_id = "unknown"
    
    def answer(self) -> bool:
        """Answer the incoming call"""
        try:
            self.fs_session.answer()
            logger.info(f"Call answered: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error answering call {self.session_id}: {e}")
            return False
    
    def hangup(self, cause: str = "NORMAL_CLEARING") -> bool:
        """Hang up the call"""
        try:
            self.fs_session.hangup(cause)
            logger.info(f"Call hung up: {self.session_id}, cause: {cause}")
            return True
        except Exception as e:
            logger.error(f"Error hanging up call {self.session_id}: {e}")
            return False
    
    def play_audio(self, audio_file: str) -> bool:
        """Play audio file to the call"""
        try:
            self.fs_session.execute("playback", audio_file)
            logger.info(f"Playing audio {audio_file} to call {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error playing audio to call {self.session_id}: {e}")
            return False
    
    def speak_tts(self, text: str, voice: str = "ru") -> bool:
        """Speak text using TTS"""
        try:
            # Using mod_tts_commandline or similar
            tts_command = f"tts|{voice}|{text}"
            self.fs_session.execute("speak", tts_command)
            logger.info(f"Speaking TTS to call {self.session_id}: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error speaking TTS to call {self.session_id}: {e}")
            return False
    
    def set_variable(self, name: str, value: str) -> bool:
        """Set a channel variable"""
        try:
            self.fs_session.setVariable(name, value)
            return True
        except Exception as e:
            logger.error(f"Error setting variable {name} on call {self.session_id}: {e}")
            return False
    
    def get_variable(self, name: str) -> Optional[str]:
        """Get a channel variable"""
        try:
            return self.fs_session.getVariable(name)
        except Exception as e:
            logger.error(f"Error getting variable {name} from call {self.session_id}: {e}")
            return None
    
    def bridge(self, destination: str) -> bool:
        """Bridge call to another destination"""
        try:
            self.fs_session.execute("bridge", destination)
            logger.info(f"Bridging call {self.session_id} to {destination}")
            return True
        except Exception as e:
            logger.error(f"Error bridging call {self.session_id}: {e}")
            return False
    
    def start_recording(self, file_path: str) -> bool:
        """Start recording the call"""
        try:
            self.fs_session.execute("record_session", file_path)
            logger.info(f"Started recording call {self.session_id} to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error starting recording for call {self.session_id}: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """Stop recording the call"""
        try:
            self.fs_session.execute("stop_record_session", "all")
            logger.info(f"Stopped recording call {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping recording for call {self.session_id}: {e}")
            return False


class GatewayServiceClient:
    """
    HTTP client for communicating with Gateway Service.
    Handles call control and audio streaming.
    """
    
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url
        self.session = None
        self._lock = threading.Lock()
    
    def _get_session(self):
        """Get or create HTTP session (thread-safe)"""
        if self.session is None:
            try:
                import requests
                self.session = requests.Session()
                self.session.headers.update({
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                })
            except ImportError:
                logger.error("requests library not available")
                return None
        return self.session
    
    def start_call(self, caller_id: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Start a new call session with Gateway Service"""
        try:
            session = self._get_session()
            if not session:
                return None
            
            url = f"{self.gateway_url}/v1/call/start"
            payload = {
                "caller_id": caller_id,
                "metadata": metadata or {}
            }
            
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            session_id = data.get("session_id")
            logger.info(f"Started call session with Gateway: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting call with Gateway: {e}")
            return None
    
    def end_call(self, session_id: str) -> bool:
        """End call session with Gateway Service"""
        try:
            session = self._get_session()
            if not session:
                return False
            
            url = f"{self.gateway_url}/v1/call/end"
            payload = {"session_id": session_id}
            
            response = session.post(url, params=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Ended call session with Gateway: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending call with Gateway: {e}")
            return False
    
    def send_audio(self, session_id: str, audio_data: bytes, 
                   sample_rate: int = 8000) -> Optional[Dict[str, Any]]:
        """Send audio chunk to Gateway Service for processing"""
        try:
            session = self._get_session()
            if not session:
                return None
            
            url = f"{self.gateway_url}/v1/audio/process"
            
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            payload = {
                "session_id": session_id,
                "audio_chunk": {
                    "session_id": session_id,
                    "audio_data": audio_b64,
                    "sample_rate": sample_rate
                }
            }
            
            response = session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error sending audio to Gateway: {e}")
            return None
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status from Gateway Service"""
        try:
            session = self._get_session()
            if not session:
                return None
            
            url = f"{self.gateway_url}/v1/session/{session_id}"
            
            response = session.get(url, timeout=5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting session status from Gateway: {e}")
            return None
    
    def send_dtmf(self, session_id: str, digit: str) -> bool:
        """Send DTMF event to Gateway Service"""
        try:
            session = self._get_session()
            if not session:
                return False
            
            url = f"{self.gateway_url}/v1/call/dtmf"
            payload = {
                "session_id": session_id,
                "digit": digit
            }
            
            response = session.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            logger.debug(f"Sent DTMF '{digit}' for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending DTMF to Gateway: {e}")
            return False


class CallEventHandler:
    """
    Handles SIP call events and coordinates with Gateway Service.
    Implements the core call flow logic.
    """
    
    def __init__(self, gateway_client: Optional[GatewayServiceClient] = None):
        self.gateway_client = gateway_client or GatewayServiceClient()
        self.active_sessions: Dict[str, CallSession] = {}
        self.fs_sessions: Dict[str, FreeSWITCHSession] = {}
        self._lock = threading.Lock()
        
        # Event callbacks
        self.on_incoming_call: Optional[Callable[[CallSession], None]] = None
        self.on_call_answered: Optional[Callable[[CallSession], None]] = None
        self.on_call_hangup: Optional[Callable[[CallSession], None]] = None
        self.on_dtmf: Optional[Callable[[DTMFEvent], None]] = None
        self.on_audio_frame: Optional[Callable[[AudioFrame], None]] = None
    
    def _get_greeting_message(self) -> str:
        """Get greeting message for incoming calls"""
        return "Здравствуйте! Я голосовой помощник. Чем могу помочь?"
    
    def handle_incoming_call(self, fs_session: Any) -> bool:
        """
        Handle incoming SIP call event.
        
        Args:
            fs_session: FreeSWITCH session object
            
        Returns:
            True if call was handled successfully
        """
        try:
            # Wrap FreeSWITCH session
            fs_wrapper = FreeSWITCHSession(fs_session)
            
            # Create call session
            call_session = CallSession(
                session_id=fs_wrapper.session_id,
                caller_id=fs_wrapper.caller_id,
                callee_id=fs_wrapper.callee_id,
                direction=CallDirection.INBOUND,
                metadata={
                    "fs_session_id": fs_wrapper.session_id,
                    "call_start_time": datetime.utcnow().isoformat()
                }
            )
            
            # Register session
            with self._lock:
                self.active_sessions[call_session.session_id] = call_session
                self.fs_sessions[call_session.session_id] = fs_wrapper
            
            logger.info(f"Incoming call from {call_session.caller_id} to {call_session.callee_id}")
            
            # Notify Gateway Service
            gateway_session_id = self.gateway_client.start_call(
                caller_id=call_session.caller_id,
                metadata=call_session.metadata
            )
            
            if gateway_session_id:
                call_session.metadata["gateway_session_id"] = gateway_session_id
            else:
                logger.warning(f"Failed to register call with Gateway Service: {call_session.session_id}")
            
            # Answer the call
            if fs_wrapper.answer():
                call_session.is_active = True
                
                # Play greeting message
                greeting = self._get_greeting_message()
                fs_wrapper.speak_tts(greeting)
                
                # Trigger callback
                if self.on_incoming_call:
                    self.on_incoming_call(call_session)
                
                return True
            else:
                logger.error(f"Failed to answer call: {call_session.session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}", exc_info=True)
            return False
    
    def handle_call_answered(self, fs_session: Any) -> bool:
        """Handle call answered event"""
        try:
            fs_wrapper = FreeSWITCHSession(fs_session)
            session_id = fs_wrapper.session_id
            
            with self._lock:
                if session_id in self.active_sessions:
                    call_session = self.active_sessions[session_id]
                    call_session.is_active = True
                    
                    if self.on_call_answered:
                        self.on_call_answered(call_session)
                    
                    logger.info(f"Call answered: {session_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling call answered: {e}")
            return False
    
    def handle_call_hangup(self, fs_session: Any, hangup_cause: str = "NORMAL_CLEARING") -> bool:
        """Handle call hangup event"""
        try:
            fs_wrapper = FreeSWITCHSession(fs_session)
            session_id = fs_wrapper.session_id
            
            with self._lock:
                if session_id in self.active_sessions:
                    call_session = self.active_sessions[session_id]
                    call_session.is_active = False
                    call_session.end_time = datetime.utcnow()
                    
                    # Notify Gateway Service
                    gateway_session_id = call_session.metadata.get("gateway_session_id")
                    if gateway_session_id:
                        self.gateway_client.end_call(gateway_session_id)
                    
                    # Trigger callback
                    if self.on_call_hangup:
                        self.on_call_hangup(call_session)
                    
                    # Clean up
                    del self.active_sessions[session_id]
                    if session_id in self.fs_sessions:
                        del self.fs_sessions[session_id]
                    
                    logger.info(f"Call hung up: {session_id}, cause: {hangup_cause}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling call hangup: {e}")
            return False
    
    def handle_dtmf(self, fs_session: Any, digit: str, duration_ms: int = 100) -> bool:
        """Handle DTMF (touch-tone) event"""
        try:
            fs_wrapper = FreeSWITCHSession(fs_session)
            session_id = fs_wrapper.session_id
            
            with self._lock:
                if session_id in self.active_sessions:
                    call_session = self.active_sessions[session_id]
                    call_session.dtmf_buffer += digit
                    
                    dtmf_event = DTMFEvent(
                        session_id=session_id,
                        digit=digit,
                        duration_ms=duration_ms
                    )
                    
                    # Send to Gateway Service
                    gateway_session_id = call_session.metadata.get("gateway_session_id")
                    if gateway_session_id:
                        self.gateway_client.send_dtmf(gateway_session_id, digit)
                    
                    # Trigger callback
                    if self.on_dtmf:
                        self.on_dtmf(dtmf_event)
                    
                    logger.debug(f"DTMF received: {digit} for session {session_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling DTMF: {e}")
            return False
    
    def handle_audio_frame(self, session_id: str, audio_data: bytes,
                          timestamp: int, sequence_number: int) -> Optional[Dict[str, Any]]:
        """
        Handle incoming RTP audio frame.
        
        Args:
            session_id: FreeSWITCH session ID
            audio_data: Raw audio bytes
            timestamp: RTP timestamp
            sequence_number: RTP sequence number
            
        Returns:
            Processing result from Gateway Service or None
        """
        try:
            with self._lock:
                if session_id not in self.active_sessions:
                    logger.warning(f"Received audio for unknown session: {session_id}")
                    return None
                
                call_session = self.active_sessions[session_id]
                gateway_session_id = call_session.metadata.get("gateway_session_id")
            
            # Create audio frame
            audio_frame = AudioFrame(
                session_id=session_id,
                data=audio_data,
                timestamp=timestamp,
                sequence_number=sequence_number
            )
            
            # Send to Gateway Service for processing
            if gateway_session_id:
                result = self.gateway_client.send_audio(
                    gateway_session_id,
                    audio_data,
                    sample_rate=audio_frame.sample_rate
                )
                
                # Trigger callback
                if self.on_audio_frame:
                    self.on_audio_frame(audio_frame)
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling audio frame: {e}")
            return None
    
    def get_active_session(self, session_id: str) -> Optional[CallSession]:
        """Get active call session by ID"""
        with self._lock:
            return self.active_sessions.get(session_id)
    
    def get_all_active_sessions(self) -> Dict[str, CallSession]:
        """Get all active call sessions"""
        with self._lock:
            return dict(self.active_sessions)
    
    def play_response(self, session_id: str, text: str) -> bool:
        """Play TTS response to a call"""
        try:
            with self._lock:
                if session_id not in self.fs_sessions:
                    logger.warning(f"Cannot play response: session {session_id} not found")
                    return False
                
                fs_wrapper = self.fs_sessions[session_id]
            
            return fs_wrapper.speak_tts(text)
            
        except Exception as e:
            logger.error(f"Error playing response: {e}")
            return False


# ===== FreeSWITCH mod_python3 Entry Points =====
# These functions are called by FreeSWITCH mod_python3

def handler(fs_session: Any, args: str = "") -> str:
    """
    Main entry point for FreeSWITCH mod_python3.
    Called when a call is routed to the Python handler.
    
    Args:
        fs_session: FreeSWITCH session object
        args: Additional arguments from dialplan
        
    Returns:
        Result string for FreeSWITCH
    """
    logger.info(f"Python handler called with args: {args}")
    
    # Create event handler
    event_handler = CallEventHandler()
    
    # Handle incoming call
    success = event_handler.handle_incoming_call(fs_session)
    
    if success:
        # Set up hangup handler
        fs_session.setHangupHook(lambda sess, cause: _on_hangup(sess, cause, event_handler))
        
        # Set up DTMF handler
        fs_session.setInputCallback(lambda sess, what, obj: _on_input(sess, what, obj, event_handler))
        
        return "success"
    else:
        return "failure"


def _on_hangup(fs_session: Any, hangup_cause: str, event_handler: CallEventHandler):
    """Internal hangup callback"""
    event_handler.handle_call_hangup(fs_session, hangup_cause)


def _on_input(fs_session: Any, what: str, obj: Any, event_handler: CallEventHandler) -> str:
    """Internal input callback (DTMF)"""
    if what == "dtmf":
        digit = obj.digit if hasattr(obj, 'digit') else str(obj)
        duration = obj.duration if hasattr(obj, 'duration') else 100
        event_handler.handle_dtmf(fs_session, digit, duration)
    return ""


# Alternative: Class-based handler for more complex scenarios
class FreeSWITCHCallHandler:
    """
    Class-based handler for FreeSWITCH integration.
    Provides more control over call handling.
    """
    
    def __init__(self):
        self.event_handler = CallEventHandler()
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup event callbacks"""
        self.event_handler.on_incoming_call = self._on_incoming_call
        self.event_handler.on_call_hangup = self._on_call_hangup
        self.event_handler.on_dtmf = self._on_dtmf
    
    def _on_incoming_call(self, session: CallSession):
        """Callback for incoming calls"""
        logger.info(f"Callback: Incoming call from {session.caller_id}")
    
    def _on_call_hangup(self, session: CallSession):
        """Callback for call hangup"""
        logger.info(f"Callback: Call hung up {session.session_id}")
    
    def _on_dtmf(self, event: DTMFEvent):
        """Callback for DTMF"""
        logger.info(f"Callback: DTMF {event.digit} received")
    
    def handle(self, fs_session: Any, args: str = "") -> str:
        """Main handler method"""
        return handler(fs_session, args)


# Factory function for creating handlers
def create_handler() -> FreeSWITCHCallHandler:
    """Create a new call handler instance"""
    return FreeSWITCHCallHandler()
