"""
Interfaces for Silero TTS plugin.
"""

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class ITtsModel(Protocol):
    """Interface for TTS model."""
    
    def apply_tts(
        self,
        text: str,
        speaker: str,
        sample_rate: int
    ) -> Any:
        """
        Apply TTS to text.
        
        Args:
            text: Text to synthesize
            speaker: Speaker identifier
            sample_rate: Target sample rate
            
        Returns:
            Audio tensor/data
        """
        ...


@runtime_checkable
class IAudioConverter(Protocol):
    """Interface for audio format converter."""
    
    def to_wav_bytes(self, audio_data: Any, sample_rate: int) -> bytes:
        """
        Convert audio data to WAV format bytes.
        
        Args:
            audio_data: Raw audio data (e.g., tensor)
            sample_rate: Audio sample rate
            
        Returns:
            WAV file bytes
        """
        ...
