"""
Vosk ASR Service implementation.

This module implements the IAsrService interface using Vosk.
All dependencies are injected via constructor - no IoC container knowledge.
"""

from typing import Dict, Optional

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseAsrService,
    TranscriptionResult
)
from ..interfaces import IVoskModel, IVoskRecognizer


class VoskAsrService(BaseAsrService):
    """
    Vosk-based ASR service implementation.
    
    This service receives its dependencies (model) through the constructor,
    making it easy to test and mock.
    """
    
    def __init__(self, model: IVoskModel):
        """
        Initialize ASR service.
        
        Args:
            model: Vosk model wrapper instance
        """
        self._model = model
        self._sessions: Dict[str, IVoskRecognizer] = {}
        self._partial_results_enabled = True
    
    async def initialize(self) -> None:
        """
        Initialize the service.
        
        Note: The model should already be initialized by the factory.
        This method is for any additional service-level initialization.
        """
        # Model is initialized by the factory before being injected
        pass
    
    async def shutdown(self) -> None:
        """Cleanup all sessions and release resources."""
        self._sessions.clear()
    
    async def transcribe(self, audio_data: bytes) -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        This is a one-shot transcription without session management.
        For streaming recognition, use start_session/end_session.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            TranscriptionResult with text and confidence
        """
        recognizer = self._model.create_recognizer()
        
        # Process all audio at once
        recognizer.accept_waveform(audio_data)
        result = recognizer.result()
        
        text = result.get("text", "")
        confidence = result.get("confidence", 0.0)
        
        return TranscriptionResult(
            text=text,
            confidence=confidence,
            is_final=True
        )
    
    async def start_session(self, session_id: str) -> None:
        """
        Start a new recognition session.
        
        Args:
            session_id: Unique session identifier
        """
        if session_id in self._sessions:
            # Session already exists, reset it
            del self._sessions[session_id]
        
        recognizer = self._model.create_recognizer()
        self._sessions[session_id] = recognizer
    
    async def end_session(self, session_id: str) -> None:
        """
        End recognition session and cleanup.
        
        Args:
            session_id: Session identifier to end
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    async def process_chunk(
        self,
        session_id: str,
        audio_chunk: bytes
    ) -> Optional[TranscriptionResult]:
        """
        Process an audio chunk in a session.
        
        Args:
            session_id: Active session identifier
            audio_chunk: Audio data chunk
            
        Returns:
            TranscriptionResult if final result is ready, None for partial
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found. Call start_session first.")
        
        recognizer = self._sessions[session_id]
        
        is_final = recognizer.accept_waveform(audio_chunk)
        
        if is_final:
            result = recognizer.result()
            return TranscriptionResult(
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                is_final=True
            )
        elif self._partial_results_enabled:
            result = recognizer.partial_result()
            return TranscriptionResult(
                text=result.get("partial", ""),
                confidence=0.0,
                is_final=False
            )
        
        return None
    
    def enable_partial_results(self, enabled: bool = True) -> None:
        """
        Enable or disable partial results.
        
        Args:
            enabled: True to enable partial results
        """
        self._partial_results_enabled = enabled
