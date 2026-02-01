from pydantic import BaseModel
from datetime import datetime


class TranscriptionDTO(BaseModel):
    """Data transfer object for ASR results"""
    text: str
    is_final: bool
    confidence: float
    timestamp: datetime
    audio_duration: float  # in seconds

    @classmethod
    def from_asr_result(cls, asr_result) -> 'TranscriptionDTO':
        """Create DTO from ASR service result"""
        return cls(
            text=asr_result.text,
            is_final=asr_result.is_final,
            confidence=asr_result.confidence,
            timestamp=asr_result.timestamp,
            audio_duration=asr_result.audio_duration
        )