"""
Tests for Gateway Service functionality
"""
import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.gateway_service.main import SessionManager
from voice_assistant.domain.entities.call_session import CallSession, SessionState
from voice_assistant.infrastructure.cache.session_cache import SessionCache
from voice_assistant.interfaces.container import Config


class TestSessionManager:
    """Test session management functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Config()
        config.session_timeout_minutes = 30
        return config
    
    @pytest.fixture
    def mock_session_cache(self):
        """Create mock session cache"""
        cache = MagicMock()
        cache.redis = AsyncMock()
        return cache
    
    @pytest.fixture
    def session_manager(self, mock_session_cache, mock_config):
        """Create session manager with mocks"""
        return SessionManager(mock_session_cache, mock_config)
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test session creation"""
        caller_id = "test_caller"
        metadata = {"test": "data"}
        
        session = await session_manager.create_session(caller_id, metadata)
        
        assert session.caller_id == caller_id
        assert session.metadata == metadata
        assert session.state == SessionState.INITIALIZING
        assert session.session_id in session_manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_update_session_state(self, session_manager):
        """Test session state updates"""
        # Create session
        session = await session_manager.create_session("test_caller")
        
        # Update to active state
        success = await session_manager.update_session_state(
            session.session_id, 
            SessionState.ACTIVE
        )
        
        assert success
        assert session.state == SessionState.ACTIVE
    
    @pytest.mark.asyncio
    async def test_invalid_state_transition(self, session_manager):
        """Test invalid state transitions are rejected"""
        # Create session
        session = await session_manager.create_session("test_caller")
        
        # Try invalid transition (INITIALIZING -> PROCESSING without going through ACTIVE)
        success = await session_manager.update_session_state(
            session.session_id, 
            SessionState.TERMINATED  # This should be allowed
        )
        
        assert success  # TERMINATED is allowed from INITIALIZING
        
        # Now try transition from TERMINATED (should fail)
        success = await session_manager.update_session_state(
            session.session_id, 
            SessionState.ACTIVE
        )
        
        assert not success  # No transitions allowed from TERMINATED
    
    @pytest.mark.asyncio
    async def test_terminate_session(self, session_manager):
        """Test session termination"""
        # Create session
        session = await session_manager.create_session("test_caller")
        
        # Terminate session
        success = await session_manager.terminate_session(session.session_id)
        
        assert success
        assert session.state == SessionState.TERMINATED
        assert session.end_time is not None
        assert session.session_id not in session_manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager):
        """Test getting non-existent session returns None"""
        fake_id = uuid4()
        session = await session_manager.get_session(fake_id)
        assert session is None


class TestCallSession:
    """Test CallSession entity functionality"""
    
    def test_create_session(self):
        """Test session creation"""
        caller_id = "test_caller"
        metadata = {"key": "value"}
        
        session = CallSession.create(caller_id, metadata)
        
        assert session.caller_id == caller_id
        assert session.metadata == metadata
        assert session.state == SessionState.INITIALIZING
        assert session.start_time is not None
        assert session.end_time is None
    
    def test_state_transitions(self):
        """Test valid state transitions"""
        session = CallSession.create("test_caller")
        
        # Valid transitions from INITIALIZING
        assert session.can_transition_to(SessionState.ACTIVE)
        assert session.can_transition_to(SessionState.ERROR)
        assert session.can_transition_to(SessionState.TERMINATED)
        
        # Invalid transition
        assert not session.can_transition_to(SessionState.PROCESSING)  # Must go through ACTIVE first
    
    def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        session = CallSession.create("test_caller")
        
        # Start active
        session.update_state(SessionState.ACTIVE)
        assert session.is_active()
        assert not session.is_terminated()
        
        # Process
        session.update_state(SessionState.PROCESSING)
        assert session.is_active()
        
        # Terminate
        session.terminate()
        assert not session.is_active()
        assert session.is_terminated()
        assert session.end_time is not None
    
    def test_session_duration(self):
        """Test session duration calculation"""
        session = CallSession.create("test_caller")
        
        # Should have duration even without end time
        duration = session.get_duration()
        assert duration is not None
        assert duration >= 0
        
        # Terminate and check duration
        session.terminate()
        duration_after_termination = session.get_duration()
        assert duration_after_termination is not None
        assert duration_after_termination >= duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])