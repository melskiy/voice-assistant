"""
Silero TTS Service implementation.
"""

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseTtsService,
)
from ..interfaces import ITtsModel, IAudioConverter


class SileroTtsService(BaseTtsService):
    """
    Silero TTS service implementation.
    
    Uses Silero TTS models for high-quality speech synthesis.
    All dependencies are injected via constructor.
    """
    
    def __init__(
        self,
        model: ITtsModel,
        audio_converter: IAudioConverter,
        speaker: str = "baya",
        sample_rate: int = 48000
    ):
        """
        Initialize TTS service.
        
        Args:
            model: TTS model instance
            audio_converter: Audio format converter
            speaker: Default speaker identifier
            sample_rate: Audio sample rate
        """
        self._model = model
        self._audio_converter = audio_converter
        self._speaker = speaker
        self._sample_rate = sample_rate
    
    async def initialize(self) -> None:
        """Initialize the service."""
        # Model is already initialized by the factory
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
            Audio data as WAV bytes
        """
        # Generate audio using Silero TTS
        audio = self._model.apply_tts(
            text=text,
            speaker=self._speaker,
            sample_rate=self._sample_rate
        )
        
        # Convert to WAV bytes
        return self._audio_converter.to_wav_bytes(audio, self._sample_rate)
    
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
