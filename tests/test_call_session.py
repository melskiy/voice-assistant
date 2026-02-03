"""
Unit and property-based tests for CallSession entity.
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta
from uuid import UUID

from voice_assistant.domain.entities.call_session import CallSession, SessionState


class TestCallSession:
    """Unit tests for CallSession entity"""
    
    def test_create_call_session(self, sample_metadata):
        """Test creating a new call session"""
        caller_id = "+1234567890"
        session = CallSession.create(caller_id, sample_metadata)
        
        assert isinstance(session.session_id, UUID)
        assert session.caller_id == caller_id
        assert session.state == SessionState.INITIALIZING
        assert session.metadata == sample_metadata
        assert session.end_time is None
        assert isinstance(session.start_time, datetime)
    
    def test_update_state(self, sample_call_session):
        """Test updating session state"""
        new_metadata = {"updated": True}
        sample_call_session.update_state(SessionState.ACTIVE, new_metadata)
        
        assert sample_call_session.state == SessionState.ACTIVE
        assert sample_call_session.metadata["updated"] is True
        assert sample_call_session.metadata["test"] is True  # Original metadata preserved
    
    def test_terminate_session(self, active_call_session):
        """Test terminating a session"""
        assert active_call_session.end_time is None
        
        active_call_session.terminate()
        
        assert active_call_session.state == SessionState.TERMINATED
        assert active_call_session.end_time is not None
        assert active_call_session.is_terminated()
    
    def test_is_active(self):
        """Test session activity status"""
        session = CallSession.create("+1234567890")
        
        # Initially not active (INITIALIZING)
        assert not session.is_active()
        
        # Active states
        for state in [SessionState.ACTIVE, SessionState.PROCESSING, SessionState.WAITING_FOR_INPUT]:
            session.update_state(state)
            assert session.is_active()
        
        # Non-active states
        for state in [SessionState.INITIALIZING, SessionState.TERMINATING, SessionState.TERMINATED, SessionState.ERROR]:
            session.update_state(state)
            assert not session.is_active()
    
    def test_get_duration(self, sample_call_session):
        """Test getting session duration"""
        # Active session duration
        duration = sample_call_session.get_duration()
        assert isinstance(duration, float)
        assert duration >= 0
        
        # Terminated session duration
        sample_call_session.terminate()
        terminated_duration = sample_call_session.get_duration()
        assert isinstance(terminated_duration, float)
        assert terminated_duration >= duration
    
    def test_state_transitions(self, sample_call_session):
        """Test valid state transitions"""
        # From INITIALIZING
        assert sample_call_session.can_transition_to(SessionState.ACTIVE)
        assert sample_call_session.can_transition_to(SessionState.ERROR)
        assert sample_call_session.can_transition_to(SessionState.TERMINATED)
        assert not sample_call_session.can_transition_to(SessionState.PROCESSING)
        
        # From ACTIVE
        sample_call_session.update_state(SessionState.ACTIVE)
        assert sample_call_session.can_transition_to(SessionState.PROCESSING)
        assert sample_call_session.can_transition_to(SessionState.WAITING_FOR_INPUT)
        assert sample_call_session.can_transition_to(SessionState.TERMINATING)
        assert not sample_call_session.can_transition_to(SessionState.INITIALIZING)
        
        # From TERMINATED (terminal state)
        sample_call_session.update_state(SessionState.TERMINATED)
        for state in SessionState:
            assert not sample_call_session.can_transition_to(state)


@pytest.mark.property
class TestCallSessionProperties:
    """Property-based tests for CallSession entity"""
    
    @given(
        caller_id=st.text(min_size=1, max_size=20),
        metadata=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.one_of(st.text(), st.integers(), st.booleans()),
            max_size=5
        )
    )
    def test_session_creation_property(self, caller_id, metadata):
        """
        Property: For any valid caller_id and metadata, CallSession.create should
        produce a valid session with correct initial state
        """
        session = CallSession.create(caller_id, metadata)
        
        # Session should have valid UUID
        assert isinstance(session.session_id, UUID)
        
        # Should preserve caller_id and metadata
        assert session.caller_id == caller_id
        assert session.metadata == metadata
        
        # Should start in INITIALIZING state
        assert session.state == SessionState.INITIALIZING
        
        # Should have valid timestamps
        assert isinstance(session.start_time, datetime)
        assert session.end_time is None
        
        # Should not be active initially
        assert not session.is_active()
        assert not session.is_terminated()
    
    @given(
        states=st.lists(
            st.sampled_from([
                SessionState.ACTIVE,
                SessionState.PROCESSING,
                SessionState.WAITING_FOR_INPUT,
                SessionState.TERMINATING
            ]),
            min_size=1,
            max_size=10
        )
    )
    def test_state_transition_sequence_property(self, states):
        """
        Property: For any sequence of valid state transitions from INITIALIZING,
        the session should maintain consistency
        """
        session = CallSession.create("+1234567890")
        
        # Start with transition to ACTIVE (always valid from INITIALIZING)
        session.update_state(SessionState.ACTIVE)
        
        previous_state = SessionState.ACTIVE
        for target_state in states:
            if session.can_transition_to(target_state):
                session.update_state(target_state)
                assert session.state == target_state
                previous_state = target_state
            
            # Session should always have valid timestamps
            assert isinstance(session.start_time, datetime)
            
            # If terminated, end_time should be set
            if session.state == SessionState.TERMINATED:
                assert session.end_time is not None
                assert session.is_terminated()
                break
    
    @given(
        metadata_updates=st.lists(
            st.dictionaries(
                st.text(min_size=1, max_size=10),
                st.one_of(st.text(), st.integers(), st.booleans()),
                max_size=3
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_metadata_accumulation_property(self, metadata_updates):
        """
        Property: For any sequence of metadata updates, the session should
        accumulate all metadata correctly without losing previous values
        """
        session = CallSession.create("+1234567890", {"initial": True})
        
        # Track all expected metadata
        expected_metadata = {"initial": True}
        
        for update in metadata_updates:
            session.update_state(session.state, update)
            expected_metadata.update(update)
            
            # All expected keys should be present
            for key, value in expected_metadata.items():
                assert key in session.metadata
                assert session.metadata[key] == value
    
    @given(st.integers(min_value=0, max_value=3600))
    def test_duration_consistency_property(self, delay_seconds):
        """
        Property: For any session, duration should be consistent and non-negative
        """
        session = CallSession.create("+1234567890")
        
        # Initial duration should be small but non-negative
        initial_duration = session.get_duration()
        assert initial_duration >= 0
        
        # Simulate time passing by manually setting start_time
        session.start_time = datetime.utcnow() - timedelta(seconds=delay_seconds)
        
        duration = session.get_duration()
        assert duration >= delay_seconds - 1  # Allow for small timing differences
        
        # After termination, duration should be fixed
        session.terminate()
        terminated_duration = session.get_duration()
        assert terminated_duration >= duration