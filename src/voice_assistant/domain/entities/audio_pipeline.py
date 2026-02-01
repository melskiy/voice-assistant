"""
Audio Pipeline entity for managing audio processing business logic.

Business concept: Core domain entity that encapsulates audio segmentation,
validation, and processing rules independent of infrastructure.
Constraints:
    - Audio chunks must be valid size
    - Sample rate and channels must match configuration
    - Incomplete chunks handled according to business rules
"""
from dataclasses import dataclass, field
from typing import List
from uuid import UUID

from ..value_objects.audio_chunk import AudioChunk
from ..value_objects.audio_segment import AudioSegment


@dataclass
class AudioPipeline:
    """
    Domain entity for audio processing pipeline.
    
    Encapsulates business rules for:
    - Audio segmentation into chunks
    - Audio validation
    - Chunk size calculations
    """
    sample_rate: int = 8000
    channels: int = 1
    bytes_per_sample: int = 2  # 16-bit audio
    chunk_duration_ms: int = 200  # 200ms chunks
    min_chunk_percentage: float = 0.5  # Minimum 50% for incomplete chunks
    
    @property
    def chunk_size_bytes(self) -> int:
        """Calculate chunk size in bytes based on configuration."""
        return int(
            (self.sample_rate * self.chunk_duration_ms * self.channels * self.bytes_per_sample) / 1000
        )
    
    def validate_audio(self, audio_data: bytes) -> bool:
        """
        Business rule: Validate audio data format.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            True if audio is valid
        """
        if not audio_data:
            return False
        
        # Check data length is multiple of sample size
        sample_size = self.channels * self.bytes_per_sample
        if len(audio_data) % sample_size != 0:
            return False
        
        return True
    
    def segment_audio(
        self, 
        audio_data: bytes, 
        session_id: UUID
    ) -> List[AudioSegment]:
        """
        Business rule: Segment raw audio into chunks.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            session_id: Session identifier for tracking
            
        Returns:
            List of AudioSegment objects
        """
        if not self.validate_audio(audio_data):
            return []
        
        segments = []
        sequence_number = 0
        
        # Handle small audio data
        if len(audio_data) < self.chunk_size_bytes:
            segment = self._create_padded_segment(
                audio_data, 
                sequence_number
            )
            if segment:
                segments.append(segment)
            return segments
        
        # Process audio in chunks
        for i in range(0, len(audio_data), self.chunk_size_bytes):
            chunk_data = audio_data[i:i + self.chunk_size_bytes]
            
            # Handle incomplete final chunk
            if len(chunk_data) < self.chunk_size_bytes:
                if len(chunk_data) >= self.chunk_size_bytes * self.min_chunk_percentage:
                    # Pad with silence if at least 50% of expected size
                    segment = self._create_padded_segment(
                        chunk_data, 
                        sequence_number
                    )
                    if segment:
                        segments.append(segment)
                # Skip very small chunks
                continue
            
            # Calculate actual duration
            actual_duration = len(chunk_data) / (
                self.sample_rate * self.channels * self.bytes_per_sample
            )
            
            segment = AudioSegment.create(
                data=chunk_data,
                sample_rate=self.sample_rate,
                channels=self.channels,
                sequence_number=sequence_number,
                duration=actual_duration,
                session_id=session_id
            )
            segments.append(segment)
            sequence_number += 1
        
        return segments
    
    def _create_padded_segment(
        self, 
        audio_data: bytes, 
        sequence_number: int
    ) -> AudioSegment:
        """
        Create a padded segment from incomplete audio data.
        
        Args:
            audio_data: Raw audio bytes (may be incomplete)
            sequence_number: Sequence number for ordering
            
        Returns:
            AudioSegment with padded data
        """
        actual_size = len(audio_data)
        
        # Pad with silence
        padded_data = audio_data + b'\x00' * (self.chunk_size_bytes - actual_size)
        
        # Calculate actual duration before padding
        actual_duration = actual_size / (
            self.sample_rate * self.channels * self.bytes_per_sample
        )
        
        return AudioSegment.create(
            data=padded_data,
            sample_rate=self.sample_rate,
            channels=self.channels,
            sequence_number=sequence_number,
            duration=actual_duration
        )
    
    def calculate_duration(self, audio_data: bytes) -> float:
        """
        Calculate audio duration in seconds.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Duration in seconds
        """
        if not audio_data:
            return 0.0
        
        bytes_per_second = (
            self.sample_rate * self.channels * self.bytes_per_sample
        )
        return len(audio_data) / bytes_per_second
    
    def create_audio_chunk(
        self,
        data: bytes,
        sequence_number: int = 0,
        is_final: bool = False
    ) -> AudioChunk:
        """
        Create an AudioChunk value object.
        
        Args:
            data: Audio data
            sequence_number: Sequence number
            is_final: Whether this is the final chunk
            
        Returns:
            AudioChunk value object
        """
        duration = self.calculate_duration(data)
        
        return AudioChunk.create(
            data=data,
            sample_rate=self.sample_rate,
            channels=self.channels,
            sequence_number=sequence_number,
            duration=duration,
            is_final=is_final
        )
