"""
ASR Service gRPC Servicer.

Implements the gRPC interface for ASR Service.
"""
import logging
from typing import Dict, Any, AsyncIterator
from datetime import datetime

import grpc

from ...infrastructure.grpc.generated import audio_pb2, audio_pb2_grpc
from ...domain.value_objects.audio_chunk import AudioChunk
from ...application.use_cases.asr_use_cases import (
    TranscribeAudioUseCase,
    ManageASRSessionUseCase
)

logger = logging.getLogger(__name__)


class ASRServiceServicer(audio_pb2_grpc.ASRServiceServicer):
    """
    gRPC servicer implementation for ASR Service.
    """
    
    def __init__(
        self,
        transcribe_use_case: TranscribeAudioUseCase,
        manage_session_use_case: ManageASRSessionUseCase
    ):
        self.transcribe_use_case = transcribe_use_case
        self.manage_session_use_case = manage_session_use_case
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("ASRServiceServicer initialized")
    
    async def ProcessAudioStream(
        self,
        request_iterator: AsyncIterator[audio_pb2.AudioChunk],
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[audio_pb2.ASRResult]:
        """Process bidirectional audio streaming."""
        session_id = None
        
        try:
            logger.info("Starting audio stream processing")
            
            async for audio_chunk_pb in request_iterator:
                try:
                    # Extract session ID from first chunk
                    if session_id is None:
                        metadata = dict(context.invocation_metadata())
                        session_id = metadata.get('session-id', f"session_{int(datetime.now().timestamp())}")
                        
                        # Initialize session stats
                        self.active_sessions[session_id] = {
                            'start_time': datetime.utcnow(),
                            'chunk_count': 0,
                            'primary_failures': 0,
                            'primary_successes': 0,
                            'fallback_used': 0,
                            'fallback_failures': 0,
                            'low_confidence_results': 0,
                            'total_failures': 0
                        }
                        logger.info(f"Started ASR session: {session_id}")
                    
                    # Convert protobuf to domain AudioChunk
                    audio_chunk = AudioChunk.create(
                        data=audio_chunk_pb.audio_data,
                        sample_rate=audio_chunk_pb.sample_rate,
                        channels=audio_chunk_pb.channels,
                        sequence_number=audio_chunk_pb.sequence_number,
                        duration=audio_chunk_pb.duration_ms / 1000.0
                    )
                    audio_chunk.is_final = audio_chunk_pb.is_final
                    
                    # Update stats
                    self.active_sessions[session_id]['chunk_count'] += 1
                    
                    # Transcribe
                    transcription = await self.transcribe_use_case.execute(
                        audio_chunk=audio_chunk,
                        session_id=session_id,
                        session_stats=self.active_sessions[session_id]
                    )
                    
                    # Convert to protobuf
                    asr_result = audio_pb2.ASRResult(
                        text=transcription.text,
                        confidence=transcription.confidence,
                        is_final=transcription.is_final,
                        timestamp_ms=int(transcription.timestamp.timestamp() * 1000),
                        session_id=session_id
                    )
                    
                    yield asr_result
                    
                    # Handle final chunk
                    if audio_chunk.is_final:
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
        finally:
            # Cleanup
            if session_id:
                await self.manage_session_use_case.end_session(session_id)
                session_info = self.active_sessions.pop(session_id, {})
                logger.info(f"Ended ASR session {session_id}: {session_info}")
    
    async def StartSession(
        self,
        request: audio_pb2.ASRRequest,
        context: grpc.aio.ServicerContext
    ) -> audio_pb2.SessionResponse:
        """Start a new ASR session."""
        try:
            session_id = request.session_id
            
            success, message = await self.manage_session_use_case.start_session(session_id)
            
            if success:
                self.active_sessions[session_id] = {
                    'start_time': datetime.utcnow(),
                    'chunk_count': 0,
                    'primary_failures': 0,
                    'primary_successes': 0,
                    'fallback_used': 0,
                    'fallback_failures': 0,
                    'low_confidence_results': 0,
                    'total_failures': 0
                }
            
            return audio_pb2.SessionResponse(
                session_id=session_id,
                success=success,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return audio_pb2.SessionResponse(
                session_id=request.session_id,
                success=False,
                message=str(e)
            )
    
    async def EndSession(
        self,
        request: audio_pb2.SessionRequest,
        context: grpc.aio.ServicerContext
    ) -> audio_pb2.SessionResponse:
        """End an ASR session."""
        try:
            session_id = request.session_id
            
            success, message = await self.manage_session_use_case.end_session(session_id)
            
            # Remove session stats
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            return audio_pb2.SessionResponse(
                session_id=session_id,
                success=success,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return audio_pb2.SessionResponse(
                session_id=request.session_id,
                success=False,
                message=str(e)
            )
