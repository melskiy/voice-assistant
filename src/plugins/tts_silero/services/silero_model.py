"""
Silero TTS model implementation.
"""

import io
from typing import Optional, Any

try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    torchaudio = None

from ..interfaces import ITtsModel, IAudioConverter


class SileroTtsModel(ITtsModel):
    """
    Silero TTS model wrapper.
    
    Wraps the Silero TTS model loaded from torch.hub.
    """
    
    def __init__(
        self,
        model: Any,
        device: str = "cpu"
    ):
        """
        Initialize model wrapper.
        
        Args:
            model: Silero TTS model instance
            device: Device the model is on (cpu/cuda)
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is not installed")
        
        self._model = model
        self._device = device
    
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
            Audio tensor
        """
        return self._model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=sample_rate
        )


class TorchAudioConverter(IAudioConverter):
    """
    Converts PyTorch tensors to WAV bytes using torchaudio.
    """
    
    def __init__(self):
        """Initialize converter."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch and torchaudio are not installed")
    
    def to_wav_bytes(self, audio_data: Any, sample_rate: int) -> bytes:
        """
        Convert audio tensor to WAV format bytes.
        
        Args:
            audio_data: Audio tensor
            sample_rate: Audio sample rate
            
        Returns:
            WAV file bytes
        """
        buffer = io.BytesIO()
        
        # Ensure audio_data is a tensor with proper shape
        if hasattr(audio_data, 'unsqueeze'):
            audio_data = audio_data.unsqueeze(0)
        
        torchaudio.save(buffer, audio_data, sample_rate, format="wav")
        
        return buffer.getvalue()


class SileroModelFactory:
    """
    Factory for creating Silero TTS model instances.
    """
    
    @staticmethod
    def create(
        model_id: str = "v3_ru.pt",
        device: str = "cpu",
        language: str = "ru"
    ) -> SileroTtsModel:
        """
        Create a Silero TTS model.
        
        Args:
            model_id: Model identifier
            device: Device to load model on
            language: Language code
            
        Returns:
            Configured SileroTtsModel instance
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is not installed")
        
        # Load model from torch.hub
        model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language=language,
            speaker=model_id
        )
        
        # Move to device
        model = model.to(device)
        
        return SileroTtsModel(model, device)
