"""
Transcribe Audio Use Case.

User goal: Convert audio to text.
Success guarantee: Returns transcription or indicates failure.
Side effects: May start/end ASR sessions.
"""
from uuid import UUID

from ...domain.value_objects.audio_chunk import AudioChunk
from ..dto.transcription_dto import TranscriptionDTO
from ..ports.asr_port import ASRPort


class TranscribeAudio:
    """
    Use case for audio transcription.
    
    Simple use case that delegates to ASR port.
    Can be extended with caching or preprocessing.
    """
    
    def __init__(self, asr_port: ASRPort):
        self.asr_port = asr_port
    
    async def execute(self, audio_chunk: AudioChunk) -> TranscriptionDTO | None:
        """
        Transcribe audio chunk.
        
        Args:
            audio_chunk: Audio data to transcribe
            
        Returns:
            Transcription result or None if failed
        """
        try:
            return await self.asr_port.transcribe(audio_chunk)
        except Exception:
            return None
    
    async def start_session(self, session_id: UUID) -> None:
        """Start ASR recognition session."""
        await self.asr_port.start_recognition_session(session_id)
    
    async def end_session(self, session_id: UUID) -> None:
        """End ASR recognition session."""
        await self.asr_port.end_recognition_session(session_id)
