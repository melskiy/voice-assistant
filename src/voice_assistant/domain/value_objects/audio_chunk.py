from pydantic import BaseModel
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime


class AudioChunk(BaseModel):
    """Value object representing a chunk of audio data"""
    id: UUID
    data: bytes
    sample_rate: int
    channels: int
    timestamp: datetime
    sequence_number: int
    duration: float  # in seconds
    is_final: bool = False

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def create(
        cls,
        data: bytes,
        sample_rate: int = 8000,
        channels: int = 1,
        sequence_number: int = 0,
        duration: float | None = None
    ) -> 'AudioChunk':
        """Factory method to create an AudioChunk"""
        if duration is None:
            duration = len(data) / (sample_rate * channels * 2)  # assuming 16-bit samples
        
        return cls(
            id=uuid4(),
            data=data,
            sample_rate=sample_rate,
            channels=channels,
            timestamp=datetime.utcnow(),
            sequence_number=sequence_number,
            duration=duration
        )