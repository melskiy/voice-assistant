"""
Session Manager service for Gateway Service.
Handles call session lifecycle and persistence.
"""
import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime

from voice_assistant.domain.entities.call_session import CallSession, SessionState
from voice_assistant.infrastructure.cache.session_cache import SessionCache
from voice_assistant.interfaces.container import Config

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages call session lifecycle.
    
    Responsibilities:
    - Create and terminate sessions
    - Update session state with validation
    - Persist sessions to Redis
    - Cleanup expired sessions
    """
    
    def __init__(self, session_cache: SessionCache, config: Config):
        """
        Initialize session manager.
        
        Args:
            session_cache: Redis-based session cache
            config: Application configuration
        """
        self.session_cache = session_cache
        self.config = config
        self.active_sessions: Dict[UUID, CallSession] = {}
    
    async def create_session(
        self,
        caller_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CallSession:
        """
        Create a new call session.
        
        Args:
            caller_id: Caller identifier (phone number)
            metadata: Optional session metadata
            
        Returns:
            Created CallSession
        """
        session = CallSession.create(caller_id, metadata)
        
        # Store in local cache
        self.active_sessions[session.session_id] = session
        
        # Store in Redis
        await self._store_call_session_in_redis(session)
        
        logger.info(f"Created new session {session.session_id} for caller {caller_id}")
        return session
    
    async def get_session(self, session_id: UUID) -> Optional[CallSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session UUID
            
        Returns:
            CallSession or None if not found
        """
        # Check local cache first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Check Redis
        session = await self._get_call_session_from_redis(session_id)
        if session:
            self.active_sessions[session_id] = session
        
        return session
    
    async def update_session_state(
        self,
        session_id: UUID,
        new_state: SessionState,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update session state with validation.
        
        Args:
            session_id: Session UUID
            new_state: New session state
            metadata_updates: Optional metadata updates
            
        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False
        
        # Validate state transition
        if not session.can_transition_to(new_state):
            logger.warning(
                f"Invalid state transition from {session.state} to {new_state} "
                f"for session {session_id}"
            )
            return False
        
        # Update state
        session.update_state(new_state, metadata_updates)
        
        # Persist to Redis
        await self._store_call_session_in_redis(session)
        
        logger.info(f"Updated session {session_id} state to {new_state}")
        return True
    
    async def terminate_session(self, session_id: UUID) -> bool:
        """
        Terminate a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found for termination: {session_id}")
            return False
        
        # Terminate
        session.terminate()
        
        # Update in Redis
        await self._store_call_session_in_redis(session)
        
        # Remove from local cache
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        logger.info(f"Terminated session {session_id}")
        return True
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of expired sessions cleaned up
        """
        expired_count = 0
        expired_sessions = []
        
        for session_id, session in list(self.active_sessions.items()):
            # Check if terminated
            if session.is_terminated():
                expired_sessions.append(session_id)
                continue
            
            # Check if inactive too long
            duration = session.get_duration()
            if duration and duration > (self.config.session_timeout_minutes * 60):
                await self.terminate_session(session_id)
                expired_sessions.append(session_id)
                expired_count += 1
        
        # Remove from local cache
        for session_id in expired_sessions:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions")
        
        return expired_count
    
    async def _store_call_session_in_redis(self, session: CallSession) -> bool:
        """
        Store CallSession in Redis.
        
        Args:
            session: CallSession to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"call_session:{session.session_id}"
            session_dict = {
                'session_id': str(session.session_id),
                'caller_id': session.caller_id,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'state': session.state.value,
                'metadata': session.metadata
            }
            
            await self.session_cache.redis.setex(
                key,
                self.config.session_timeout_minutes * 60,
                json.dumps(session_dict, ensure_ascii=False)
            )
            return True
        except Exception as e:
            logger.error(f"Error storing call session in Redis: {e}")
            return False
    
    async def _get_call_session_from_redis(self, session_id: UUID) -> Optional[CallSession]:
        """
        Get CallSession from Redis.
        
        Args:
            session_id: Session UUID
            
        Returns:
            CallSession or None if not found
        """
        try:
            key = f"call_session:{session_id}"
            data = await self.session_cache.redis.get(key)
            
            if not data:
                return None
            
            session_dict = json.loads(data)
            
            session = CallSession(
                session_id=UUID(session_dict['session_id']),
                caller_id=session_dict['caller_id'],
                start_time=datetime.fromisoformat(session_dict['start_time']),
                end_time=datetime.fromisoformat(session_dict['end_time']) if session_dict['end_time'] else None,
                state=SessionState(session_dict['state']),
                metadata=session_dict['metadata']
            )
            
            return session
        except Exception as e:
            logger.error(f"Error getting call session from Redis: {e}")
            return None