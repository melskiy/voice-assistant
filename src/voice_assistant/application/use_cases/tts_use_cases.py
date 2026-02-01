"""
TTS Use Cases for TTS Service.

User goal: Synthesize speech from text.
Success guarantee: Returns audio data.
Side effects: None (stateless operation).
"""
from typing import List, Optional, AsyncIterator

from ...domain.services.text_normalizer import RussianTextNormalizer
from ...infrastructure.plugins.plugin_interface import TTSPlugin


class SynthesizeSpeechUseCase:
    """
    Use case for synthesizing speech.
    
    Normalizes text and uses TTS plugin for synthesis.
    """
    
    def __init__(
        self,
        tts_plugin: TTSPlugin,
        text_normalizer: Optional[RussianTextNormalizer] = None
    ):
        self.tts_plugin = tts_plugin
        self.text_normalizer = text_normalizer or RussianTextNormalizer()
    
    async def execute(self, text: str) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio data as bytes
        """
        # Normalize text
        normalized_text = self.text_normalizer.normalize(text)
        
        # Synthesize
        audio_bytes = await self.tts_plugin.synthesize(normalized_text)
        
        return audio_bytes
    
    async def execute_streaming(
        self,
        text: str,
        chunk_size: int = 3200
    ) -> AsyncIterator[bytes]:
        """
        Synthesize speech with streaming output.
        
        Args:
            text: Text to synthesize
            chunk_size: Size of each chunk in bytes
            
        Yields:
            Audio chunks
        """
        audio_bytes = await self.execute(text)
        
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]


class GetAvailableVoicesUseCase:
    """Use case for getting available TTS voices."""
    
    def execute(self, language: Optional[str] = None) -> List[dict]:
        """
        Get list of available voices.
        
        Args:
            language: Optional language filter
            
        Returns:
            List of voice info dictionaries
        """
        voices = [
            {
                "voice_id": "silero_ru_baya",
                "name": "Baya (Russian Female)",
                "language": "ru",
                "gender": "female",
                "metadata": {
                    "model": "silero_tts_v3",
                    "speaker": "baya",
                    "quality": "high"
                }
            },
            {
                "voice_id": "silero_ru_aidar",
                "name": "Aidar (Russian Male)",
                "language": "ru",
                "gender": "male",
                "metadata": {
                    "model": "silero_tts_v3",
                    "speaker": "aidar",
                    "quality": "high"
                }
            }
        ]
        
        if language:
            voices = [v for v in voices if v["language"] == language]
        
        return voices
