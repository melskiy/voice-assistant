"""
Session management views for Gateway Service.
"""
import logging
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime

from fastapi import Request, HTTPException, Query

from .base import BaseViewSet, viewset
from ..schemas import (
    StartCallRequest,
    EndCallRequest,
    SessionResponse,
    SessionStatusResponse,
    SessionInfo,
    SessionListResponse,
    CleanupResponse,
    SessionStateUpdateRequest,
)
from ...application.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


@viewset("sessions", "/sessions")
class SessionViewSet(BaseViewSet):
    """
    ViewSet for session management endpoints.
    Handles call session lifecycle operations.
    """
    
    tags = ["Sessions"]
    
    def _register_routes(self) -> None:
        """Register session management routes"""
        # Session lifecycle
        self.router.add_api_route(
            "/start",
            self.start_call,
            methods=["POST"],
            response_model=SessionResponse,
            summary="Start a new call session",
            description="Create and initialize a new call session",
        )
        
        self.router.add_api_route(
            "/end",
            self.end_call,
            methods=["POST"],
            response_model=SessionResponse,
            summary="End a call session",
            description="Terminate an active call session",
        )
        
        # Session queries
        self.router.add_api_route(
            "/{session_id}",
            self.get_session_status,
            methods=["GET"],
            response_model=SessionStatusResponse,
            summary="Get session status",
            description="Get detailed status of a specific session",
        )
        
        self.router.add_api_route(
            "",
            self.list_sessions,
            methods=["GET"],
            response_model=SessionListResponse,
            summary="List sessions",
            description="List all sessions with optional filtering",
        )
        
        # Session management
        self.router.add_api_route(
            "/cleanup",
            self.cleanup_sessions,
            methods=["POST"],
            response_model=CleanupResponse,
            summary="Cleanup expired sessions",
            description="Remove expired and terminated sessions",
        )
        
        self.router.add_api_route(
            "/{session_id}/state",
            self.update_session_state,
            methods=["PUT"],
            response_model=SessionResponse,
            summary="Update session state",
            description="Update the state of a session",
        )

    def _get_session_manager(self, request: Request) -> SessionManager:
        """Get or create session manager instance"""
        session_cache = self.require_state_attr(request, "session_cache")
        config = self.require_state_attr(request, "config")
        return SessionManager(session_cache, config)

    async def start_call(
        self,
        request_data: StartCallRequest,
        request: Request
    ) -> SessionResponse:
        """
        Start a new call session.
        
        Args:
            request_data: Call start request data
            request: FastAPI request object
            
        Returns:
            SessionResponse with new session details
        """
        try:
            session_manager = self._get_session_manager(request)
            
            # Create new session
            session = await session_manager.create_session(
                request_data.caller_id,
                request_data.metadata
            )
            
            # Update state to active
            await session_manager.update_session_state(
                session.session_id,
                session.state.ACTIVE
            )
            
            # Start ASR session via gRPC to ASR Service
            # Note: ASR plugin (Vosk) is loaded by ASR Service, not Gateway
            audio_manager = self.get_state_attr(request, "audio_stream_manager")
            if audio_manager:
                asr_started = await audio_manager.start_session_with_asr(
                    session.session_id,
                    language="ru"
                )
                if not asr_started:
                    logger.warning(f"Failed to start ASR session for {session.session_id}")
            
            logger.info(f"Started call for session {session.session_id}")
            
            return SessionResponse(
                session_id=str(session.session_id),
                status="started",
                message="Call session started successfully",
                state=session.state.value
            )
            
        except Exception as e:
            logger.error(f"Error starting call: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def end_call(
        self,
        request_data: EndCallRequest,
        request: Request
    ) -> SessionResponse:
        """
        End a call session.
        
        Args:
            request_data: Call end request data
            request: FastAPI request object
            
        Returns:
            SessionResponse with termination result
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(request_data.session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Terminate session
            success = await session_manager.terminate_session(session_uuid)
            if not success:
                raise self.handle_error("Failed to terminate session", status_code=500)
            
            # End ASR session via gRPC to ASR Service
            audio_manager = self.get_state_attr(request, "audio_stream_manager")
            if audio_manager:
                await audio_manager.end_session_with_asr(session_uuid)
            
            logger.info(f"Ended call for session {request_data.session_id}")
            
            return SessionResponse(
                session_id=request_data.session_id,
                status="ended",
                message=f"Call session ended: {request_data.reason or 'Normal clearing'}",
                state=session.state.TERMINATED.value
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error ending call: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def get_session_status(
        self,
        session_id: str,
        request: Request
    ) -> SessionStatusResponse:
        """
        Get session status.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            
        Returns:
            SessionStatusResponse with session details
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            session_info = SessionInfo(
                session_id=session_id,
                caller_id=session.caller_id,
                state=session.state.value,
                is_active=session.is_active(),
                duration_seconds=session.get_duration(),
                start_time=session.start_time,
                end_time=session.end_time,
                metadata=session.metadata
            )
            
            return SessionStatusResponse(
                session_id=session_id,
                status="active" if session.is_active() else "inactive",
                message=f"Session is {session.state.value}",
                state=session.state.value,
                session_info=session_info
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session status: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def list_sessions(
        self,
        request: Request,
        active_only: bool = Query(False, description="Show only active sessions"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of sessions")
    ) -> SessionListResponse:
        """
        List all sessions.
        
        Args:
            request: FastAPI request object
            active_only: Filter for active sessions only
            limit: Maximum number of sessions to return
            
        Returns:
            SessionListResponse with session list
        """
        try:
            session_manager = self._get_session_manager(request)
            
            sessions = []
            active_count = 0
            
            for session_id, session in session_manager.active_sessions.items():
                if active_only and not session.is_active():
                    continue
                    
                if session.is_active():
                    active_count += 1
                
                sessions.append(SessionInfo(
                    session_id=str(session_id),
                    caller_id=session.caller_id,
                    state=session.state.value,
                    is_active=session.is_active(),
                    duration_seconds=session.get_duration(),
                    start_time=session.start_time,
                    end_time=session.end_time,
                    metadata=session.metadata
                ))
                
                if len(sessions) >= limit:
                    break
            
            return SessionListResponse(
                sessions=sessions,
                total_count=len(sessions),
                active_count=active_count
            )
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def cleanup_sessions(
        self,
        request: Request
    ) -> CleanupResponse:
        """
        Cleanup expired sessions.
        
        Args:
            request: FastAPI request object
            
        Returns:
            CleanupResponse with cleanup results
        """
        try:
            session_manager = self._get_session_manager(request)
            
            expired_count = await session_manager.cleanup_expired_sessions()
            
            return CleanupResponse(
                status="success",
                message=f"Cleaned up {expired_count} expired sessions",
                expired_count=expired_count
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def update_session_state(
        self,
        session_id: str,
        request_data: SessionStateUpdateRequest,
        request: Request
    ) -> SessionResponse:
        """
        Update session state.
        
        Args:
            session_id: Session ID
            request_data: State update request
            request: FastAPI request object
            
        Returns:
            SessionResponse with update result
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Parse new state
            from voice_assistant.domain.entities.call_session import SessionState
            try:
                new_state = SessionState(request_data.new_state)
            except ValueError:
                valid_states = [s.value for s in SessionState]
                raise self.handle_error(
                    f"Invalid state. Valid states: {valid_states}",
                    status_code=400
                )
            
            # Update state
            success = await session_manager.update_session_state(
                session_uuid,
                new_state,
                request_data.metadata_updates
            )
            
            if not success:
                raise self.handle_error(
                    f"Invalid state transition from {session.state} to {new_state}",
                    status_code=400
                )
            
            return SessionResponse(
                session_id=session_id,
                status="updated",
                message=f"Session state updated to {new_state.value}",
                state=new_state.value
            )
            
        except ValueError as e:
            if "Invalid session ID" in str(e):
                raise self.handle_error("Invalid session ID format", status_code=400)
            raise
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating session state: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)