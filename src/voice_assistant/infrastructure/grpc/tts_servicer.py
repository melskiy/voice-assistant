"""
TTS Service gRPC Servicer.

Implements the gRPC interface for TTS Service.
"""
import logging
from typing import AsyncIterator

import grpc

from ...infrastructure.grpc.generated import tts_pb2, tts_pb2_grpc
from ...infrastructure.grpc.generated import audio_pb2
from ...application.use_cases.tts_use_cases import (
    SynthesizeSpeechUseCase,
    GetAvailableVoicesUseCase
)

logger = logging.getLogger(__name__)


class TTSServiceServicer(tts_pb2_grpc.TTSServiceServicer):
    """
    gRPC servicer implementation for TTS Service.
    """
    
    def __init__(
        self,
        synthesize_use_case: SynthesizeSpeechUseCase,
        get_voices_use_case: GetAvailableVoicesUseCase
    ):
        self.synthesize_use_case = synthesize_use_case
        self.get_voices_use_case = get_voices_use_case
        logger.info("TTSServiceServicer initialized")
    
    async def SynthesizeSpeech(self, request, context):
        """
        Synthesize speech from text and stream audio chunks.
        """
        try:
            logger.info(f"Processing TTS request for session {request.session_id}")
            
            # Synthesize speech
            audio_bytes = await self.synthesize_use_case.execute(request.text)
            
            # Stream in chunks
            chunk_size = 3200  # 200ms of audio at 16kHz, 16-bit mono
            total_chunks = 0
            timestamp = 0
            
            for i in range(0, len(audio_bytes), chunk_size):
                chunk_data = audio_bytes[i:i + chunk_size]
                
                audio_chunk = audio_pb2.AudioChunk(
                    session_id=request.session_id,
                    data=chunk_data,
                    timestamp=timestamp,
                    chunk_id=f"tts-chunk-{total_chunks}"
                )
                
                yield audio_chunk
                
                total_chunks += 1
                timestamp += 200  # 200ms per chunk
            
            logger.info(
                f"TTS synthesis complete for session {request.session_id}: "
                f"{total_chunks} chunks"
            )
            
        except Exception as e:
            logger.error(f"Error during speech synthesis: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
    
    async def GetAvailableVoices(self, request, context):
        """Get list of available TTS voices."""
        try:
            voices_data = self.get_voices_use_case.execute(
                language=request.language if request.language else None
            )
            
            voices = []
            for voice_data in voices_data:
                voice = tts_pb2.VoiceInfo(
                    voice_id=voice_data["voice_id"],
                    name=voice_data["name"],
                    language=voice_data["language"],
                    gender=voice_data["gender"]
                )
                # Add metadata
                for key, value in voice_data["metadata"].items():
                    voice.metadata[key] = value
                voices.append(voice)
            
            return tts_pb2.VoicesResponse(voices=voices)
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return tts_pb2.VoicesResponse()
