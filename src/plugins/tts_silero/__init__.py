"""
Silero TTS Plugin.

This plugin provides high-quality text-to-speech using Silero models.

Usage:
    from rodi import Container
    from plugins.tts_silero import SileroTtsPluginRegistration
    
    container = Container()
    config = {"speaker": "baya", "sample_rate": 48000}
    SileroTtsPluginRegistration.register(container, config)
    
    # Resolve and use the service
    tts_service = container.resolve(ITtsService)
    audio_data = await tts_service.synthesize("Привет, мир!")
"""

from .registration import SileroTtsPluginRegistration
from .interfaces import ITtsModel, IAudioConverter
from .services.silero_model import SileroTtsModel, TorchAudioConverter, SileroModelFactory
from .services.tts_service import SileroTtsService

__all__ = [
    # Registration
    "SileroTtsPluginRegistration",
    # Interfaces
    "ITtsModel",
    "IAudioConverter",
    # Services
    "SileroTtsModel",
    "TorchAudioConverter",
    "SileroModelFactory",
    "SileroTtsService",
]
