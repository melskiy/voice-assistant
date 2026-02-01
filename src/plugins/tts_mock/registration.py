"""
Mock TTS Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    ITtsService
)
from ..interfaces import IAudioGenerator, IDelaySimulator
from .services.audio_generator import WavAudioGenerator, DelaySimulator
from .services.tts_service import MockTtsService


class MockTtsPluginRegistration(IPluginRegistration):
    """
    Registration class for Mock TTS plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="tts.mock",
            name="Mock TTS",
            version="1.0.0",
            description="Mock text-to-speech for testing",
            author="Voice Assistant Team",
            dependencies=[]  # No external dependencies
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            JSON Schema for configuration validation
        """
        return {
            "type": "object",
            "properties": {
                "delay_ms": {
                    "type": "integer",
                    "default": 0,
                    "description": "Simulated processing delay in milliseconds"
                },
                "sample_rate": {
                    "type": "integer",
                    "default": 16000,
                    "description": "Audio sample rate"
                },
                "duration_ms": {
                    "type": "integer",
                    "default": 500,
                    "description": "Base duration of generated audio in milliseconds"
                }
            },
            "required": []
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if plugin is available.
        
        Mock TTS is always available.
        
        Returns:
            Always True
        """
        return True
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register Mock TTS dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Extract configuration
        delay_ms = config.get("delay_ms", 0)
        sample_rate = config.get("sample_rate", 16000)
        duration_ms = config.get("duration_ms", 500)
        
        # Register configuration as named instance
        container.add_instance(config, name="tts_mock_config")
        
        # Register audio generator as singleton
        def audio_generator_factory(c: Container) -> IAudioGenerator:
            return WavAudioGenerator(
                sample_rate=sample_rate,
                duration_ms=duration_ms
            )
        
        container.add_singleton(IAudioGenerator, audio_generator_factory)
        
        # Register delay simulator as singleton
        def delay_simulator_factory(c: Container) -> IDelaySimulator:
            return DelaySimulator(delay_ms=delay_ms)
        
        container.add_singleton(IDelaySimulator, delay_simulator_factory)
        
        # Register TTS service as singleton
        def service_factory(c: Container) -> ITtsService:
            audio_generator = c.resolve(IAudioGenerator)
            delay_simulator = c.resolve(IDelaySimulator)
            return MockTtsService(
                audio_generator=audio_generator,
                delay_simulator=delay_simulator
            )
        
        container.add_singleton(ITtsService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
