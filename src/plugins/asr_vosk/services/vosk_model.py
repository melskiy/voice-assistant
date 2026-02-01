"""
Vosk model implementation.

This module contains the concrete implementation of Vosk model wrapper.
It has no knowledge of the IoC container - dependencies are injected via constructor.
"""

import os
from typing import Optional, TYPE_CHECKING

from ..interfaces import IVoskModel, IVoskRecognizer

if TYPE_CHECKING:
    from vosk import Model, KaldiRecognizer


class VoskModelWrapper(IVoskModel):
    """
    Wrapper around Vosk Model.
    
    This class encapsulates the Vosk model and provides a clean interface
    for creating recognizers. It is completely decoupled from the plugin
    registration logic.
    """
    
    def __init__(self, model_path: str, sample_rate: int = 8000):
        """
        Initialize Vosk model wrapper.
        
        Args:
            model_path: Path to the Vosk model directory
            sample_rate: Audio sample rate (default: 8000)
        """
        self._model_path = model_path
        self._sample_rate = sample_rate
        self._model: Optional['Model'] = None
        self._vosk_module = None
    
    async def initialize(self) -> bool:
        """
        Load the Vosk model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            from vosk import Model
            self._vosk_module = __import__('vosk')
            
            if not os.path.exists(self._model_path):
                raise FileNotFoundError(f"Vosk model not found at: {self._model_path}")
            
            self._model = Model(self._model_path)
            return True
            
        except ImportError:
            raise RuntimeError("Vosk library not installed. Install with: pip install vosk")
        except Exception as e:
            raise RuntimeError(f"Failed to load Vosk model: {e}")
    
    async def shutdown(self) -> None:
        """Release model resources."""
        self._model = None
    
    @property
    def sample_rate(self) -> int:
        """Get the model's expected sample rate."""
        return self._sample_rate
    
    def create_recognizer(self) -> 'VoskRecognizerWrapper':
        """
        Create a new recognizer instance.
        
        Returns:
            New recognizer wrapper instance
        """
        if self._model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        from vosk import KaldiRecognizer
        recognizer = KaldiRecognizer(self._model, self._sample_rate)
        return VoskRecognizerWrapper(recognizer)


class VoskRecognizerWrapper(IVoskRecognizer):
    """
    Wrapper around Vosk KaldiRecognizer.
    
    Provides a clean interface for speech recognition operations.
    """
    
    def __init__(self, recognizer: 'KaldiRecognizer'):
        """
        Initialize recognizer wrapper.
        
        Args:
            recognizer: Vosk KaldiRecognizer instance
        """
        self._recognizer = recognizer
    
    def accept_waveform(self, audio_data: bytes) -> bool:
        """
        Process audio data.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            True if final result is ready, False for partial result
        """
        return self._recognizer.AcceptWaveform(audio_data)
    
    def result(self) -> dict:
        """Get final recognition result."""
        import json
        return json.loads(self._recognizer.Result())
    
    def partial_result(self) -> dict:
        """Get partial recognition result."""
        import json
        return json.loads(self._recognizer.PartialResult())
    
    def reset(self) -> None:
        """Reset recognizer for new session."""
        # Vosk recognizer doesn't have a direct reset, 
        # we create a new one via the model
        pass


class VoskModelFactory:
    """
    Factory for creating Vosk model instances.
    
    This factory centralizes model creation logic and makes testing easier.
    """
    
    @staticmethod
    def create(config: dict) -> VoskModelWrapper:
        """
        Create a Vosk model wrapper from configuration.
        
        Args:
            config: Configuration dictionary with 'model_path' and optional 'sample_rate'
            
        Returns:
            Configured VoskModelWrapper instance
        """
        model_path = config.get("model_path")
        sample_rate = config.get("sample_rate", 8000)
        
        if not model_path:
            raise ValueError("model_path is required in configuration")
        
        return VoskModelWrapper(model_path, sample_rate)
