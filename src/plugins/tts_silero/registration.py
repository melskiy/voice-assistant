"""
Silero TTS Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    ITtsService
)
from ..interfaces import ITtsModel, IAudioConverter
from .services.silero_model import SileroModelFactory, TorchAudioConverter
from .services.tts_service import SileroTtsService


class SileroTtsPluginRegistration(IPluginRegistration):
    """
    Registration class for Silero TTS plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="tts.silero",
            name="Silero TTS",
            version="1.0.0",
            description="High-quality text-to-speech using Silero models",
            author="Voice Assistant Team",
            dependencies=["torch", "torchaudio"]
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
                "model_id": {
                    "type": "string",
                    "default": "v3_ru.pt",
                    "description": "Model identifier for Silero TTS"
                },
                "sample_rate": {
                    "type": "integer",
                    "default": 48000,
                    "description": "Output audio sample rate"
                },
                "speaker": {
                    "type": "string",
                    "default": "baya",
                    "description": "Speaker identifier"
                },
                "device": {
                    "type": "string",
                    "default": "cpu",
                    "enum": ["cpu", "cuda"],
                    "description": "Device to run the model on"
                },
                "language": {
                    "type": "string",
                    "default": "ru",
                    "description": "Language code"
                }
            },
            "required": []
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if PyTorch is available.
        
        Returns:
            True if torch and torchaudio are installed
        """
        try:
            import torch
            import torchaudio
            return True
        except ImportError:
            return False
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register Silero TTS dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Extract configuration
        model_id = config.get("model_id", "v3_ru.pt")
        sample_rate = config.get("sample_rate", 48000)
        speaker = config.get("speaker", "baya")
        device = config.get("device", "cpu")
        language = config.get("language", "ru")
        
        # Register configuration as named instance
        container.add_instance(config, name="tts_silero_config")
        
        # Register TTS model as singleton with lazy initialization
        async def model_factory() -> ITtsModel:
            return SileroModelFactory.create(
                model_id=model_id,
                device=device,
                language=language
            )
        
        container.add_singleton(ITtsModel, model_factory)
        
        # Register audio converter as singleton
        def converter_factory(c: Container) -> IAudioConverter:
            return TorchAudioConverter()
        
        container.add_singleton(IAudioConverter, converter_factory)
        
        # Register TTS service as singleton
        def service_factory(c: Container) -> ITtsService:
            model = c.resolve(ITtsModel)
            converter = c.resolve(IAudioConverter)
            return SileroTtsService(
                model=model,
                audio_converter=converter,
                speaker=speaker,
                sample_rate=sample_rate
            )
        
        container.add_singleton(ITtsService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
