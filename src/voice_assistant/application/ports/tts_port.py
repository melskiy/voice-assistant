"""
TTS Port - Interface for Text-to-Speech services.

User goal: Synthesize speech from text.
Success guarantee: Returns audio data or indicates failure.
Side effects: None (stateless operation).
"""
from typing import AsyncIterator, Protocol
from uuid import UUID

from ...domain.value_objects.audio_chunk import AudioChunk


class TTSPort(Protocol):
    """
    Port interface for TTS (Text-to-Speech) services.
    
    Infrastructure adapters must implement this interface to provide
    text-to-speech synthesis capabilities.
    """
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio data as bytes
            
        Raises:
            TTSError: If synthesis fails
        """
        ...
    
    async def synthesize_streaming(
        self, 
        text: str
    ) -> AsyncIterator[AudioChunk]:
        """
        Synthesize speech with streaming output.
        
        Args:
            text: Text to synthesize
            
        Yields:
            Audio chunks as they are generated
        """
        ...
    
    async def synthesize_to_file(self, text: str, output_path: str) -> None:
        """
        Synthesize speech to audio file.
        
        Args:
            text: Text to synthesize
            output_path: Path to save audio file
        """
        ...
    
    def is_available(self) -> bool:
        """
        Check if TTS service is available.
        
        Returns:
            True if service is ready to accept requests
        """
        ...
