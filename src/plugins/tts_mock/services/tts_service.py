"""
Mock TTS Service implementation.
"""

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseTtsService,
)
from ..interfaces import IAudioGenerator, IDelaySimulator


class MockTtsService(BaseTtsService):
    """
    Mock TTS service for testing.
    
    Generates dummy audio data and optionally simulates processing delay.
    All dependencies are injected via constructor.
    """
    
    def __init__(
        self,
        audio_generator: IAudioGenerator,
        delay_simulator: IDelaySimulator
    ):
        """
        Initialize TTS service.
        
        Args:
            audio_generator: Audio data generator
            delay_simulator: Delay simulator for testing
        """
        self._audio_generator = audio_generator
        self._delay_simulator = delay_simulator
    
    async def initialize(self) -> None:
        """Initialize the service."""
        # No initialization needed for mock
        pass
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        pass
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Dummy audio data as bytes
        """
        # Simulate processing delay
        await self._delay_simulator.simulate_delay()
        
        # Generate audio
        return self._audio_generator.generate(text)
    
    async def synthesize_to_file(self, text: str, output_path: str) -> None:
        """
        Synthesize speech and save to file.
        
        Args:
            text: Text to synthesize
            output_path: Path to save audio file
        """
        audio_data = await self.synthesize(text)
        
        with open(output_path, 'wb') as f:
            f.write(audio_data)
