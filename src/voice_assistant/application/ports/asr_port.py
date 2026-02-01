"""
ASR Port - Interface for Automatic Speech Recognition services.

User goal: Transcribe audio to text with confidence scoring.
Success guarantee: Returns transcription or indicates failure.
Side effects: May start/stop recognition sessions.
"""
from typing import Protocol
from uuid import UUID

from ...domain.value_objects.audio_chunk import AudioChunk
from ..dto.transcription_dto import TranscriptionDTO


class ASRPort(Protocol):
    """
    Port interface for ASR (Automatic Speech Recognition) services.
    
    Infrastructure adapters must implement this interface to provide
    speech-to-text capabilities.
    """
    
    async def transcribe(self, audio_chunk: AudioChunk) -> TranscriptionDTO:
        """
        Transcribe audio chunk to text.
        
        Args:
            audio_chunk: Audio data to transcribe
            
        Returns:
            Transcription result with text and confidence
            
        Raises:
            ASRError: If transcription fails
        """
        ...
    
    async def start_recognition_session(self, session_id: UUID) -> None:
        """
        Start a new recognition session.
        
        Args:
            session_id: Unique session identifier
        """
        ...
    
    async def end_recognition_session(self, session_id: UUID) -> None:
        """
        End recognition session and cleanup resources.
        
        Args:
            session_id: Unique session identifier
        """
        ...
    
    def is_available(self) -> bool:
        """
        Check if ASR service is available.
        
        Returns:
            True if service is ready to accept requests
        """
        ...
