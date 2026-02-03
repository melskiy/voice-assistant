"""
Interfaces for Vosk ASR plugin.

This module defines the contracts that the Vosk plugin implements.
All interfaces are pure protocols with no implementation.
"""

from typing import Protocol, Optional, runtime_checkable


@runtime_checkable
class IVoskModel(Protocol):
    """Interface for Vosk model wrapper."""
    
    @property
    def sample_rate(self) -> int:
        """Get the model's expected sample rate."""
        ...
    
    def create_recognizer(self) -> 'IVoskRecognizer':
        """Create a new recognizer instance."""
        ...


@runtime_checkable
class IVoskRecognizer(Protocol):
    """Interface for Vosk recognizer."""
    
    def accept_waveform(self, audio_data: bytes) -> bool:
        """
        Process audio data.
        
        Returns:
            True if final result is ready, False for partial result.
        """
        ...
    
    def result(self) -> dict:
        """Get final recognition result."""
        ...
    
    def partial_result(self) -> dict:
        """Get partial recognition result."""
        ...
    
    def reset(self) -> None:
        """Reset recognizer for new session."""
        ...
