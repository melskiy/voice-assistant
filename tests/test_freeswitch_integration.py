"""
Tests for FreeSWITCH integration module.
Tests cover call event handling, RTP streaming, and call routing.
"""
import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from voice_assistant.infrastructure.external.freeswitch import (
    CallEventType,
    CallDirection,
    CallSession,
    AudioFrame,
    DTMFEvent,
    FreeSWITCHSession,
    GatewayServiceClient,
    CallEventHandler,
    RTPPacket,
    AudioBuffer,
    PCMDecoder,
    RTPStreamHandler,
    RTPStreamManager,
    CallRouteType,
    CallPriority,
    RoutingRule,
    SessionContext,
    CallRouter,
    SessionManager,
    CallFlowOrchestrator,
)


# ===== Fixtures =====

@pytest.fixture
def mock_fs_session():
    """Create a mock FreeSWITCH session"""
    session = Mock()
    session.getUUID.return_value = "test-session-uuid-123"
    session.getVariable.side_effect = lambda var: {
        "caller_id_number": "+1234567890",
        "destination_number": "+0987654321"
    }.get(var)
    return session


@pytest.fixture
def mock_gateway_client():
    """Create a mock Gateway Service client"""
    client = Mock(spec=GatewayServiceClient)
    client.start_call.return_value = "gateway-session-123"
    client.end_call.return_value = True
    client.send_audio.return_value = {"text": "test", "confidence": 0.9}
    client.send_dtmf.return_value = True
    return client


@pytest.fixture
def call_event_handler(mock_gateway_client):
    """Create a CallEventHandler with mock client"""
    return CallEventHandler(gateway_client=mock_gateway_client)


@pytest.fixture
def sample_call_session():
    """Create a sample call session"""
    return CallSession(
        session_id="test-session-uuid-123",
        caller_id="+1234567890",
        callee_id="+0987654321",
        direction=CallDirection.INBOUND,
        metadata={"test": "data"}
    )


# ===== Test CallSession =====

class TestCallSession:
    """Test CallSession domain entity"""
    
    def test_create_session(self):
        """Test creating a call session"""
        session = CallSession(
            session_id="test-123",
            caller_id="+1234567890",
            callee_id="+0987654321",
            direction=CallDirection.INBOUND
        )
        
        assert session.session_id == "test-123"
        assert session.caller_id == "+1234567890"
        assert session.callee_id == "+0987654321"
        assert session.direction == CallDirection.INBOUND
        assert session.is_active is True
        assert session.dtmf_buffer == ""
    
    def test_session_to_dict(self, sample_call_session):
        """Test converting session to dictionary"""
        data = sample_call_session.to_dict()
        
        assert data["session_id"] == "test-session-uuid-123"
        assert data["caller_id"] == "+1234567890"
        assert data["direction"] == "inbound"
        assert "start_time" in data


# ===== Test FreeSWITCHSession =====

class TestFreeSWITCHSession:
    """Test FreeSWITCHSession wrapper"""
    
    def test_extract_session_info(self, mock_fs_session):
        """Test extracting session information"""
        wrapper = FreeSWITCHSession(mock_fs_session)
        
        assert wrapper.session_id == "test-session-uuid-123"
        assert wrapper.caller_id == "+1234567890"
        assert wrapper.callee_id == "+0987654321"
    
    def test_answer_call(self, mock_fs_session):
        """Test answering a call"""
        wrapper = FreeSWITCHSession(mock_fs_session)
        
        result = wrapper.answer()
        
        assert result is True
        mock_fs_session.answer.assert_called_once()
    
    def test_hangup_call(self, mock_fs_session):
        """Test hanging up a call"""
        wrapper = FreeSWITCHSession(mock_fs_session)
        
        result = wrapper.hangup("NORMAL_CLEARING")
        
        assert result is True
        mock_fs_session.hangup.assert_called_once_with("NORMAL_CLEARING")
    
    def test_play_audio(self, mock_fs_session):
        """Test playing audio file"""
        wrapper = FreeSWITCHSession(mock_fs_session)
        
        result = wrapper.play_audio("/path/to/audio.wav")
        
        assert result is True
        mock_fs_session.execute.assert_called_once_with("playback", "/path/to/audio.wav")
    
    def test_speak_tts(self, mock_fs_session):
        """Test TTS speech"""
        wrapper = FreeSWITCHSession(mock_fs_session)
        
        result = wrapper.speak_tts("Hello world", voice="ru")
        
        assert result is True
        mock_fs_session.execute.assert_called_once()
        call_args = mock_fs_session.execute.call_args[0]
        assert call_args[0] == "speak"
        assert "Hello world" in call_args[1]


# ===== Test CallEventHandler =====

class TestCallEventHandler:
    """Test CallEventHandler"""
    
    def test_handle_incoming_call(self, call_event_handler, mock_fs_session):
        """Test handling incoming call"""
        result = call_event_handler.handle_incoming_call(mock_fs_session)
        
        assert result is True
        assert "test-session-uuid-123" in call_event_handler.active_sessions
        
        # Verify Gateway Service was called
        call_event_handler.gateway_client.start_call.assert_called_once()
    
    def test_handle_call_hangup(self, call_event_handler, mock_fs_session):
        """Test handling call hangup"""
        # First create a session
        call_event_handler.handle_incoming_call(mock_fs_session)
        
        # Then hangup
        result = call_event_handler.handle_call_hangup(mock_fs_session, "NORMAL_CLEARING")
        
        assert result is True
        assert "test-session-uuid-123" not in call_event_handler.active_sessions
        
        # Verify Gateway Service was called
        call_event_handler.gateway_client.end_call.assert_called_once()
    
    def test_handle_dtmf(self, call_event_handler, mock_fs_session):
        """Test handling DTMF"""
        # First create a session
        call_event_handler.handle_incoming_call(mock_fs_session)
        
        # Send DTMF
        result = call_event_handler.handle_dtmf(mock_fs_session, "1", 100)
        
        assert result is True
        session = call_event_handler.active_sessions["test-session-uuid-123"]
        assert session.dtmf_buffer == "1"
    
    def test_handle_audio_frame(self, call_event_handler, mock_fs_session):
        """Test handling audio frame"""
        # First create a session
        call_event_handler.handle_incoming_call(mock_fs_session)
        
        # Send audio
        audio_data = b"\x00\x01\x02\x03"
        result = call_event_handler.handle_audio_frame(
            "test-session-uuid-123",
            audio_data,
            timestamp=0,
            sequence_number=0
        )
        
        # Verify Gateway Service was called
        call_event_handler.gateway_client.send_audio.assert_called_once()


# ===== Test RTP Packet =====

class TestRTPPacket:
    """Test RTP packet parsing and creation"""
    
    def test_rtp_packet_from_bytes(self):
        """Test parsing RTP packet from bytes"""
        # Create a minimal RTP packet
        # Version=2, Padding=0, Extension=0, CSRC=0 -> 0x80
        # Marker=0, Payload=0 (PCMU) -> 0x00
        # Sequence = 0x1234
        # Timestamp = 0x567890AB
        # SSRC = 0xCDEF0123
        packet_bytes = bytes([
            0x80, 0x00,  # First two bytes
            0x12, 0x34,  # Sequence number
            0x56, 0x78, 0x90, 0xAB,  # Timestamp
            0xCD, 0xEF, 0x01, 0x23,  # SSRC
            0x01, 0x02, 0x03, 0x04   # Payload
        ])
        
        packet = RTPPacket.from_bytes(packet_bytes)
        
        assert packet.version == 2
        assert packet.payload_type == 0
        assert packet.sequence_number == 0x1234
        assert packet.timestamp == 0x567890AB
        assert packet.ssrc == 0xCDEF0123
        assert packet.payload == bytes([0x01, 0x02, 0x03, 0x04])
    
    def test_rtp_packet_to_bytes(self):
        """Test serializing RTP packet to bytes"""
        packet = RTPPacket(
            version=2,
            payload_type=0,
            sequence_number=0x1234,
            timestamp=0x567890AB,
            ssrc=0xCDEF0123,
            payload=bytes([0x01, 0x02, 0x03, 0x04])
        )
        
        data = packet.to_bytes()
        
        assert len(data) == 16  # 12 bytes header + 4 bytes payload
        assert data[0] == 0x80
        assert data[1] == 0x00


# ===== Test AudioBuffer =====

class TestAudioBuffer:
    """Test AudioBuffer"""
    
    def test_add_and_get_packet(self):
        """Test adding and retrieving packets"""
        buffer = AudioBuffer(max_size=10)
        packet = RTPPacket(sequence_number=1, payload=b"test")
        
        buffer.add_packet(packet)
        retrieved = buffer.get_packet()
        
        assert retrieved is not None
        assert retrieved.sequence_number == 1
    
    def test_buffer_size_limit(self):
        """Test buffer size limit"""
        buffer = AudioBuffer(max_size=2)
        
        buffer.add_packet(RTPPacket(sequence_number=1))
        buffer.add_packet(RTPPacket(sequence_number=2))
        buffer.add_packet(RTPPacket(sequence_number=3))  # Should drop oldest
        
        assert buffer.size() == 2


# ===== Test PCM Decoder =====

class TestPCMDecoder:
    """Test G.711 PCM decoder"""
    
    def test_decode_mulaw(self):
        """Test mu-law decoding"""
        # Initialize table
        PCMDecoder._init_mulaw_table()
        
        # Test with silence (0xFF in mu-law is approximately 0)
        mulaw_data = bytes([0xFF, 0xFF])
        pcm_data = PCMDecoder.decode_mulaw(mulaw_data)
        
        assert len(pcm_data) == 4  # 2 samples * 2 bytes
    
    def test_decode_alaw(self):
        """Test A-law decoding"""
        alaw_data = bytes([0xD5, 0xD5])
        pcm_data = PCMDecoder.decode_alaw(alaw_data)
        
        assert len(pcm_data) == 4  # 2 samples * 2 bytes


# ===== Test CallRouter =====

class TestCallRouter:
    """Test CallRouter"""
    
    def test_add_rule(self):
        """Test adding routing rule"""
        router = CallRouter()
        rule = RoutingRule(
            name="test_rule",
            route_type=CallRouteType.DIRECT,
            priority=CallPriority.HIGH
        )
        
        result = router.add_rule(rule)
        
        assert result is True
        assert len(router.get_rules()) == 1
    
    def test_route_call_direct(self):
        """Test direct call routing"""
        router = CallRouter()
        rule = RoutingRule(
            name="direct_rule",
            route_type=CallRouteType.DIRECT,
            condition={"caller_pattern": r"\+123.*"},
            priority=CallPriority.NORMAL
        )
        router.add_rule(rule)
        
        matched_rule = router.route_call("+1234567890", "+0987654321")
        
        assert matched_rule is not None
        assert matched_rule.name == "direct_rule"
    
    def test_route_call_reject(self):
        """Test call rejection routing"""
        router = CallRouter()
        rule = RoutingRule(
            name="block_rule",
            route_type=CallRouteType.REJECT,
            condition={"caller_pattern": r"\+999.*"},
            priority=CallPriority.HIGH
        )
        router.add_rule(rule)
        
        matched_rule = router.route_call("+9991234567", "+0987654321")
        
        assert matched_rule is not None
        assert matched_rule.route_type == CallRouteType.REJECT


# ===== Test SessionManager =====

class TestSessionManager:
    """Test SessionManager"""
    
    def test_create_session(self, mock_fs_session, mock_gateway_client):
        """Test creating a session"""
        manager = SessionManager(gateway_client=mock_gateway_client)
        
        fs_wrapper = FreeSWITCHSession(mock_fs_session)
        context = manager.create_session(
            caller_id="+1234567890",
            callee_id="+0987654321",
            fs_session=fs_wrapper,
            route_type=CallRouteType.DIRECT
        )
        
        assert context is not None
        assert context.session.caller_id == "+1234567890"
        assert context.route_type == CallRouteType.DIRECT
        
        # Verify Gateway Service was called
        mock_gateway_client.start_call.assert_called_once()
    
    def test_get_session(self, mock_fs_session, mock_gateway_client):
        """Test retrieving a session"""
        manager = SessionManager(gateway_client=mock_gateway_client)
        
        fs_wrapper = FreeSWITCHSession(mock_fs_session)
        context = manager.create_session(
            caller_id="+1234567890",
            callee_id="+0987654321",
            fs_session=fs_wrapper
        )
        
        retrieved = manager.get_session(context.session.session_id)
        
        assert retrieved is not None
        assert retrieved.session.session_id == context.session.session_id
    
    def test_end_session(self, mock_fs_session, mock_gateway_client):
        """Test ending a session"""
        manager = SessionManager(gateway_client=mock_gateway_client)
        
        fs_wrapper = FreeSWITCHSession(mock_fs_session)
        context = manager.create_session(
            caller_id="+1234567890",
            callee_id="+0987654321",
            fs_session=fs_wrapper
        )
        
        result = manager.end_session(context.session.session_id)
        
        assert result is True
        assert manager.get_session(context.session.session_id) is None
        
        # Verify Gateway Service was called
        mock_gateway_client.end_call.assert_called_once()


# ===== Test CallFlowOrchestrator =====

class TestCallFlowOrchestrator:
    """Test CallFlowOrchestrator"""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = CallFlowOrchestrator()
        
        assert orchestrator.call_router is not None
        assert orchestrator.session_manager is not None
    
    def test_add_routing_rule(self):
        """Test adding routing rule through orchestrator"""
        orchestrator = CallFlowOrchestrator()
        rule = RoutingRule(
            name="test_rule",
            route_type=CallRouteType.DIRECT,
            priority=CallPriority.NORMAL
        )
        
        result = orchestrator.add_routing_rule(rule)
        
        assert result is True
    
    def test_get_stats(self):
        """Test getting orchestrator stats"""
        orchestrator = CallFlowOrchestrator()
        
        stats = orchestrator.get_stats()
        
        assert "routing_rules" in stats
        assert "total_sessions" in stats
        assert "active_sessions" in stats


# ===== Integration Tests =====

class TestFreeSWITCHIntegration:
    """Integration tests for FreeSWITCH module"""
    
    def test_complete_call_flow(self, mock_fs_session, mock_gateway_client):
        """Test complete call flow from incoming to hangup"""
        # Create orchestrator
        orchestrator = CallFlowOrchestrator(mock_gateway_client)
        
        # Add routing rule
        rule = RoutingRule(
            name="test_rule",
            route_type=CallRouteType.DIRECT,
            priority=CallPriority.NORMAL
        )
        orchestrator.add_routing_rule(rule)
        
        # Handle incoming call
        fs_wrapper = FreeSWITCHSession(mock_fs_session)
        result = orchestrator.handle_incoming_call(fs_wrapper)
        
        assert result is True
        
        # Get session
        session_id = fs_wrapper.session_id
        context = orchestrator.get_session(session_id)
        assert context is not None
        
        # End call
        result = orchestrator.end_call(session_id)
        assert result is True
        
        # Verify session is gone
        assert orchestrator.get_session(session_id) is None
    
    def test_dtmf_handling(self, mock_fs_session, mock_gateway_client):
        """Test DTMF handling in call flow"""
        orchestrator = CallFlowOrchestrator(mock_gateway_client)
        
        # Create session
        fs_wrapper = FreeSWITCHSession(mock_fs_session)
        orchestrator.handle_incoming_call(fs_wrapper)
        
        session_id = fs_wrapper.session_id
        
        # Handle DTMF
        result = orchestrator.session_manager.handle_dtmf(session_id, "1")
        assert result is True
        
        # Verify DTMF was sent to Gateway
        mock_gateway_client.send_dtmf.assert_called_with(
            mock_gateway_client.start_call.return_value,
            "1"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
