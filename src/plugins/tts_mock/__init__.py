"""
Mock TTS Plugin.

This plugin provides mock text-to-speech functionality for testing.

Usage:
    from rodi import Container
    from plugins.tts_mock import MockTtsPluginRegistration
    
    container = Container()
    config = {"delay_ms": 100}
    MockTtsPluginRegistration.register(container, config)
    
    # Resolve and use the service
    tts_service = container.resolve(ITtsService)
    audio_data = await tts_service.synthesize("Hello, world!")
"""

from .registration import MockTtsPluginRegistration
from .interfaces import IAudioGenerator, IDelaySimulator
from .services.audio_generator import WavAudioGenerator, DelaySimulator
from .services.tts_service import MockTtsService

__all__ = [
    # Registration
    "MockTtsPluginRegistration",
    # Interfaces
    "IAudioGenerator",
    "IDelaySimulator",
    # Services
    "WavAudioGenerator",
    "DelaySimulator",
    "MockTtsService",
]
