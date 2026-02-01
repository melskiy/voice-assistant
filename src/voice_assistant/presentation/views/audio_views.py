"""
Audio processing views for Gateway Service.
"""
import asyncio
import logging
from typing import Any, Dict, List
from uuid import UUID
from datetime import datetime

from fastapi import Request, HTTPException

from .base import BaseViewSet, viewset
from ..schemas import (
    ProcessAudioRequest,
    AudioProcessingResponse,
    AudioStatsResponse,
    ASRResult,
)
from ...application.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


@viewset("audio", "/audio")
class AudioViewSet(BaseViewSet):
    """
    ViewSet for audio processing endpoints.
    Handles audio stream processing and ASR operations.
    """
    
    tags = ["Audio"]
    
    def _register_routes(self) -> None:
        """Register audio processing routes"""
        self.router.add_api_route(
            "/process",
            self.process_audio,
            methods=["POST"],
            response_model=AudioProcessingResponse,
            summary="Process audio chunk",
            description="Process an incoming audio chunk through ASR pipeline",
        )
        
        self.router.add_api_route(
            "/stats",
            self.get_audio_stats,
            methods=["GET"],
            response_model=AudioStatsResponse,
            summary="Get audio statistics",
            description="Get audio stream processing statistics",
        )

    def _get_session_manager(self, request: Request) -> SessionManager:
        """Get or create session manager instance"""
        session_cache = self.require_state_attr(request, "session_cache")
        config = self.require_state_attr(request, "config")
        return SessionManager(session_cache, config)

    async def process_audio(
        self,
        request_data: ProcessAudioRequest,
        request: Request
    ) -> AudioProcessingResponse:
        """
        Process incoming audio chunk.
        
        Args:
            request_data: Audio processing request
            request: FastAPI request object
            
        Returns:
            AudioProcessingResponse with ASR results
        """
        try:
            session_manager = self._get_session_manager(request)
            audio_stream_manager = self.require_state_attr(request, "audio_stream_manager")
            
            # Validate session
            session_uuid = UUID(request_data.session_id)
            session = await session_manager.get_session(session_uuid)
            
            if not session:
                raise self.handle_error("Session not found", status_code=404)
            
            if not session.is_active():
                raise self.handle_error("Session is not active", status_code=400)
            
            # Update session state to processing
            from voice_assistant.domain.entities.call_session import SessionState
            await session_manager.update_session_state(
                session_uuid,
                SessionState.PROCESSING
            )
            
            logger.info(f"Processing audio for session {request_data.session_id}")
            
            # Process audio through streaming pipeline
            asr_results: List[Dict[str, Any]] = []
            try:
                async for result in audio_stream_manager.process_rtp_audio(
                    session_uuid,
                    request_data.audio_chunk.audio_data
                ):
                    asr_results.append(result)
                    logger.debug(f"ASR result: {result}")
            except Exception as e:
                logger.error(f"Error in audio processing pipeline: {e}")
                # Fallback response
                asr_results = [{
                    "text": "Ошибка обработки аудио",
                    "confidence": 0.0,
                    "is_final": True,
                    "timestamp": datetime.now(),
                    "session_id": request_data.session_id
                }]
            
            # Extract final result
            final_result = None
            for result in asr_results:
                if result.get("is_final", False):
                    final_result = result
                    break
            
            if not final_result and asr_results:
                final_result = asr_results[-1]
            
            # Convert to ASRResult objects
            asr_result_objects = [
                ASRResult(
                    text=r.get("text", ""),
                    confidence=r.get("confidence", 0.0),
                    is_final=r.get("is_final", True),
                    timestamp=r.get("timestamp"),
                    session_id=r.get("session_id")
                )
                for r in asr_results
            ]
            
            # Update session state back to active
            await session_manager.update_session_state(
                session_uuid,
                SessionState.ACTIVE
            )
            
            return AudioProcessingResponse(
                session_id=request_data.session_id,
                status="processed",
                response_text=final_result["text"] if final_result else "Пример ответа от системы",
                confidence=final_result["confidence"] if final_result else 0.5,
                is_final=final_result.get("is_final", True) if final_result else True,
                timestamp=asyncio.get_running_loop().time(),
                asr_results_count=len(asr_results),
                asr_results=asr_result_objects
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def get_audio_stats(
        self,
        request: Request
    ) -> AudioStatsResponse:
        """
        Get audio stream statistics.
        
        Args:
            request: FastAPI request object
            
        Returns:
            AudioStatsResponse with audio statistics
        """
        try:
            audio_stream_manager = self.get_state_attr(request, "audio_stream_manager")
            
            if not audio_stream_manager:
                raise self.handle_error(
                    "Audio stream manager not available",
                    status_code=503
                )
            
            stats = audio_stream_manager.get_stream_stats()
            
            return AudioStatsResponse(
                status="success",
                stats=stats,
                timestamp=asyncio.get_running_loop().time(),
                active_streams=stats.get("active_streams", 0),
                total_streams_processed=stats.get("total_streams", 0)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting audio stats: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)