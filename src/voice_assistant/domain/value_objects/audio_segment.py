"""
Audio Segment value object for representing a segment of audio data.

Business concept: Immutable value object representing a segment of audio
with metadata. Used in audio pipeline processing.
Constraints:
    - Immutable after creation
    - Contains both padded and actual duration information
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AudioSegment:
    """
    Value object representing an audio segment.
    
    Attributes:
        id: Unique identifier
        data: Audio data bytes (may be padded)
        sample_rate: Sample rate in Hz
        channels: Number of channels
        timestamp: Creation timestamp
        sequence_number: Order in sequence
        duration: Actual duration in seconds (before padding)
        padded_duration: Duration including padding
        session_id: Associated session ID
        is_final: Whether this is the final segment
    """
    id: UUID
    data: bytes
    sample_rate: int
    channels: int
    timestamp: datetime
    sequence_number: int
    duration: float  # Actual duration
    padded_duration: float  # Duration with padding
    session_id: Optional[UUID] = None
    is_final: bool = False
    
    @classmethod
    def create(
        cls,
        data: bytes,
        sample_rate: int = 8000,
        channels: int = 1,
        sequence_number: int = 0,
        duration: Optional[float] = None,
        session_id: Optional[UUID] = None,
        is_final: bool = False
    ) -> 'AudioSegment':
        """
        Factory method to create an AudioSegment.
        
        Args:
            data: Audio data bytes
            sample_rate: Sample rate in Hz
            channels: Number of channels
            sequence_number: Order in sequence
            duration: Actual duration (calculated if None)
            session_id: Associated session ID
            is_final: Whether this is the final segment
            
        Returns:
            New AudioSegment instance
        """
        # Calculate durations
        bytes_per_sample = 2  # 16-bit
        padded_duration = len(data) / (sample_rate * channels * bytes_per_sample)
        
        if duration is None:
            duration = padded_duration
        
        return cls(
            id=uuid4(),
            data=data,
            sample_rate=sample_rate,
            channels=channels,
            timestamp=datetime.utcnow(),
            sequence_number=sequence_number,
            duration=duration,
            padded_duration=padded_duration,
            session_id=session_id,
            is_final=is_final
        )
    
    def get_size_bytes(self) -> int:
        """Get the size of audio data in bytes."""
        return len(self.data)
    
    def get_padding_ratio(self) -> float:
        """
        Get the ratio of padding to actual data.
        
        Returns:
            Ratio between 0.0 (no padding) and 1.0 (all padding)
        """
        if self.padded_duration == 0:
            return 0.0
        return 1.0 - (self.duration / self.padded_duration)
    
    def is_mostly_padding(self, threshold: float = 0.5) -> bool:
        """
        Check if segment is mostly padding.
        
        Args:
            threshold: Ratio threshold (default 0.5 = 50%)
            
        Returns:
            True if padding ratio exceeds threshold
        """
        return self.get_padding_ratio() > threshold
