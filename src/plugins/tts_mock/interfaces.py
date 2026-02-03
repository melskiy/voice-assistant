"""
Interfaces for Mock TTS plugin.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class IAudioGenerator(Protocol):
    """Interface for audio data generator."""
    
    def generate(self, text: str) -> bytes:
        """
        Generate audio data for the given text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio data as bytes
        """
        ...


@runtime_checkable
class IDelaySimulator(Protocol):
    """Interface for delay simulation."""
    
    async def simulate_delay(self) -> None:
        """Simulate processing delay."""
        ...
