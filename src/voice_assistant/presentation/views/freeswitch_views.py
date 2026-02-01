"""
FreeSWITCH integration views for Gateway Service.
"""
import asyncio
import logging
from typing import Any, Dict, List
from uuid import UUID
from datetime import datetime

from fastapi import Request, HTTPException, Query

from .base import BaseViewSet, viewset
from ..schemas import (
    StartCallRequest,
    DTMFRequest,
    RTPStreamRequest,
    RTPStreamResponse,
    GreetingRequest,
    CallControlResponse,
    FreeSwitchSessionResponse,
    FreeSwitchStatsResponse,
    ActiveSessionInfo,
    SessionResponse,
)
from ...application.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


@viewset("freeswitch", "/freeswitch")
class FreeSwitchViewSet(BaseViewSet):
    """
    ViewSet for FreeSWITCH integration endpoints.
    Handles incoming calls, RTP streams, and call control from FreeSWITCH.
    """
    
    tags = ["FreeSWITCH"]
    
    def _register_routes(self) -> None:
        """Register FreeSWITCH integration routes"""
        # Call lifecycle
        self.router.add_api_route(
            "/call/incoming",
            self.handle_incoming_call,
            methods=["POST"],
            response_model=SessionResponse,
            summary="Handle incoming call",
            description="Handle incoming call from FreeSWITCH",
        )
        
        self.router.add_api_route(
            "/call/answer",
            self.answer_call,
            methods=["POST"],
            response_model=CallControlResponse,
            summary="Answer call",
            description="Mark call as answered",
        )
        
        self.router.add_api_route(
            "/call/hangup",
            self.hangup_call,
            methods=["POST"],
            response_model=CallControlResponse,
            summary="Hangup call",
            description="Handle call hangup from FreeSWITCH",
        )
        
        # DTMF and RTP
        self.router.add_api_route(
            "/dtmf",
            self.handle_dtmf,
            methods=["POST"],
            response_model=CallControlResponse,
            summary="Handle DTMF",
            description="Handle DTMF (touch-tone) event from FreeSWITCH",
        )
        
        self.router.add_api_route(
            "/rtp/setup",
            self.setup_rtp_stream,
            methods=["POST"],
            response_model=RTPStreamResponse,
            summary="Setup RTP stream",
            description="Setup RTP audio stream for session",
        )
        
        # Audio playback
        self.router.add_api_route(
            "/greeting/play",
            self.play_greeting,
            methods=["POST"],
            response_model=CallControlResponse,
            summary="Play greeting",
            description="Prepare greeting message for playback",
        )
        
        self.router.add_api_route(
            "/response/play",
            self.play_response,
            methods=["POST"],
            response_model=CallControlResponse,
            summary="Play response",
            description="Prepare response text for playback via TTS",
        )
        
        # Session info
        self.router.add_api_route(
            "/session/{session_id}",
            self.get_session_status,
            methods=["GET"],
            response_model=FreeSwitchSessionResponse,
            summary="Get session status",
            description="Get detailed session status for FreeSWITCH",
        )
        
        self.router.add_api_route(
            "/stats",
            self.get_stats,
            methods=["GET"],
            response_model=FreeSwitchStatsResponse,
            summary="Get statistics",
            description="Get FreeSWITCH integration statistics",
        )

    def _get_session_manager(self, request: Request) -> SessionManager:
        """Get or create session manager instance"""
        session_cache = self.require_state_attr(request, "session_cache")
        config = self.require_state_attr(request, "config")
        return SessionManager(session_cache, config)

    async def handle_incoming_call(
        self,
        request_data: StartCallRequest,
        request: Request
    ) -> SessionResponse:
        """
        Handle incoming call from FreeSWITCH.
        
        Args:
            request_data: Call start request
            request: FastAPI request object
            
        Returns:
            SessionResponse with new session details
        """
        try:
            session_manager = self._get_session_manager(request)
            
            # Create session with FreeSWITCH metadata
            metadata = request_data.metadata or {}
            metadata["source"] = "freeswitch"
            metadata["incoming_time"] = datetime.utcnow().isoformat()
            
            session = await session_manager.create_session(
                request_data.caller_id,
                metadata
            )
            
            # Update state to active
            from voice_assistant.domain.entities.call_session import SessionState
            await session_manager.update_session_state(
                session.session_id,
                SessionState.ACTIVE
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
            else:
                logger.warning("Audio stream manager not available")
            
            logger.info(f"FreeSWITCH incoming call: {session.session_id} from {request_data.caller_id}")
            
            return SessionResponse(
                session_id=str(session.session_id),
                status="accepted",
                message="Call accepted and session created",
                state=session.state.value
            )
            
        except Exception as e:
            logger.error(f"Error handling FreeSWITCH incoming call: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def answer_call(
        self,
        session_id: str,
        request: Request
    ) -> CallControlResponse:
        """
        Mark call as answered.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            
        Returns:
            CallControlResponse with result
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Update state
            from voice_assistant.domain.entities.call_session import SessionState
            success = await session_manager.update_session_state(
                session_uuid,
                SessionState.ACTIVE,
                metadata_updates={"answered_time": datetime.utcnow().isoformat()}
            )
            
            if not success:
                raise self.handle_error("Failed to update session state", status_code=500)
            
            logger.info(f"FreeSWITCH call answered: {session_id}")
            
            return CallControlResponse(
                session_id=session_id,
                status="success",
                message="Call marked as answered",
                action="answer"
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error answering FreeSWITCH call: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def hangup_call(
        self,
        session_id: str,
        request: Request,
        hangup_cause: str = "NORMAL_CLEARING"
    ) -> CallControlResponse:
        """
        Handle call hangup from FreeSWITCH.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            hangup_cause: Reason for hangup
            
        Returns:
            CallControlResponse with result
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(session_id)
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
            
            logger.info(f"FreeSWITCH call hung up: {session_id}, cause: {hangup_cause}")
            
            return CallControlResponse(
                session_id=session_id,
                status="success",
                message=f"Call hung up: {hangup_cause}",
                action="hangup"
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error hanging up FreeSWITCH call: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def handle_dtmf(
        self,
        request_data: DTMFRequest,
        request: Request
    ) -> CallControlResponse:
        """
        Handle DTMF event from FreeSWITCH.
        
        Args:
            request_data: DTMF request
            request: FastAPI request object
            
        Returns:
            CallControlResponse with result
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(request_data.session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Update session metadata with DTMF
            await session_manager.update_session_state(
                session_uuid,
                session.state,
                metadata_updates={
                    "last_dtmf": request_data.digit,
                    "last_dtmf_time": datetime.utcnow().isoformat()
                }
            )
            
            logger.debug(f"DTMF received for session {request_data.session_id}: {request_data.digit}")
            
            return CallControlResponse(
                session_id=request_data.session_id,
                status="success",
                message=f"DTMF '{request_data.digit}' processed",
                action="dtmf"
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling DTMF: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def setup_rtp_stream(
        self,
        request_data: RTPStreamRequest,
        request: Request
    ) -> RTPStreamResponse:
        """
        Setup RTP audio stream.
        
        Args:
            request_data: RTP stream setup request
            request: FastAPI request object
            
        Returns:
            RTPStreamResponse with setup result
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(request_data.session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Store RTP configuration
            rtp_config = {
                "rtp_local_port": request_data.local_port,
                "rtp_remote_host": request_data.remote_host,
                "rtp_remote_port": request_data.remote_port,
                "rtp_payload_type": request_data.payload_type,
                "rtp_sample_rate": request_data.sample_rate,
                "rtp_setup_time": datetime.utcnow().isoformat()
            }
            
            await session_manager.update_session_state(
                session_uuid,
                session.state,
                metadata_updates=rtp_config
            )
            
            logger.info(f"RTP stream setup for session {request_data.session_id} on port {request_data.local_port}")
            
            return RTPStreamResponse(
                session_id=request_data.session_id,
                local_port=request_data.local_port,
                status="success",
                message="RTP stream configured"
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting up RTP stream: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def play_greeting(
        self,
        request_data: GreetingRequest,
        request: Request
    ) -> CallControlResponse:
        """
        Prepare greeting message for playback.
        
        Args:
            request_data: Greeting request
            request: FastAPI request object
            
        Returns:
            CallControlResponse with greeting text
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(request_data.session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Determine greeting message
            greeting = request_data.message
            if not greeting:
                greeting = "Здравствуйте! Я голосовой помощник. Чем могу помочь?"
            
            # Update session metadata
            await session_manager.update_session_state(
                session_uuid,
                session.state,
                metadata_updates={
                    "greeting_played": True,
                    "greeting_message": greeting,
                    "greeting_time": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Greeting prepared for session {request_data.session_id}")
            
            return CallControlResponse(
                session_id=request_data.session_id,
                status="success",
                message=greeting,
                action="play_greeting"
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error playing greeting: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def play_response(
        self,
        session_id: str,
        text: str,
        request: Request
    ) -> CallControlResponse:
        """
        Prepare response text for playback.
        
        Args:
            session_id: Session ID
            text: Response text
            request: FastAPI request object
            
        Returns:
            CallControlResponse with response text
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            # Update session metadata
            await session_manager.update_session_state(
                session_uuid,
                session.state,
                metadata_updates={
                    "last_response": text,
                    "last_response_time": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Response prepared for session {session_id}: {text[:50]}...")
            
            return CallControlResponse(
                session_id=session_id,
                status="success",
                message=text,
                action="play_response"
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error playing response: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def get_session_status(
        self,
        session_id: str,
        request: Request
    ) -> FreeSwitchSessionResponse:
        """
        Get detailed session status.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            
        Returns:
            FreeSwitchSessionResponse with session details
        """
        try:
            session_manager = self._get_session_manager(request)
            
            session_uuid = UUID(session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            return FreeSwitchSessionResponse(
                session_id=session_id,
                caller_id=session.caller_id,
                state=session.state.value,
                is_active=session.is_active(),
                duration_seconds=session.get_duration(),
                metadata=session.metadata,
                start_time=session.start_time,
                end_time=session.end_time
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session status: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def get_stats(
        self,
        request: Request
    ) -> FreeSwitchStatsResponse:
        """
        Get FreeSWITCH integration statistics.
        
        Args:
            request: FastAPI request object
            
        Returns:
            FreeSwitchStatsResponse with statistics
        """
        try:
            session_manager = self._get_session_manager(request)
            
            # Get all active sessions
            active_sessions = []
            for session_id, session in session_manager.active_sessions.items():
                if session.is_active():
                    active_sessions.append(ActiveSessionInfo(
                        session_id=str(session_id),
                        caller_id=session.caller_id,
                        state=session.state.value,
                        duration_seconds=session.get_duration()
                    ))
            
            return FreeSwitchStatsResponse(
                status="success",
                active_sessions_count=len(active_sessions),
                active_sessions=active_sessions,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting FreeSWITCH stats: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)