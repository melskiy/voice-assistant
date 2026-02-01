"""
Vosk ASR Plugin.

This plugin provides offline speech recognition using the Vosk library.

Usage:
    from rodi import Container
    from plugins.asr_vosk import VoskAsrPluginRegistration
    
    container = Container()
    config = {"model_path": "/path/to/model", "sample_rate": 8000}
    VoskAsrPluginRegistration.register(container, config)
    
    # Resolve and use the service
    asr_service = container.resolve(IAsrService)
    result = await asr_service.transcribe(audio_data)
"""

from .registration import VoskAsrPluginRegistration
from .interfaces import IVoskModel, IVoskRecognizer
from .services.vosk_model import VoskModelWrapper, VoskRecognizerWrapper, VoskModelFactory
from .services.asr_service import VoskAsrService

__all__ = [
    # Registration
    "VoskAsrPluginRegistration",
    # Interfaces
    "IVoskModel",
    "IVoskRecognizer",
    # Services
    "VoskModelWrapper",
    "VoskRecognizerWrapper",
    "VoskModelFactory",
    "VoskAsrService",
]
