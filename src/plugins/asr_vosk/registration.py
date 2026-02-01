"""
Vosk ASR Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
NO business logic should be placed here - only dependency registration.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    IAsrService
)
from .interfaces import IVoskModel
from .services.vosk_model import VoskModelFactory, VoskModelWrapper
from .services.asr_service import VoskAsrService


class VoskAsrPluginRegistration(IPluginRegistration):
    """
    Registration class for Vosk ASR plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    It does not contain any business logic or service implementation details.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="asr.vosk",
            name="Vosk ASR",
            version="1.0.0",
            description="Offline speech recognition using Vosk",
            author="Voice Assistant Team",
            dependencies=["vosk"]
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
                "model_path": {
                    "type": "string",
                    "description": "Path to Vosk model directory"
                },
                "sample_rate": {
                    "type": "integer",
                    "default": 8000,
                    "description": "Audio sample rate (Hz)"
                },
                "partial_results": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable partial transcription results"
                }
            },
            "required": ["model_path"]
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if Vosk is available in the current environment.
        
        Returns:
            True if vosk library is installed
        """
        try:
            import vosk
            return True
        except ImportError:
            return False
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register Vosk ASR dependencies in the IoC container.
        
        This method registers:
        - Configuration as a named instance
        - IVoskModel as a singleton (lazy initialization)
        - IAsrService as a singleton
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Validate required configuration
        if "model_path" not in config:
            raise ValueError("Vosk ASR plugin requires 'model_path' in configuration")
        
        # Register configuration as named instance
        container.add_instance(config, name="vosk_config")
        
        # Register model as singleton with lazy initialization
        # The factory will be called when the model is first resolved
        async def model_factory():
            model = VoskModelFactory.create(config)
            await model.initialize()
            return model
        
        # Register the model factory
        container.add_singleton(IVoskModel, model_factory)
        
        # Register ASR service as singleton
        # It will receive IVoskModel via constructor injection
        def service_factory(c: Container) -> IAsrService:
            model = c.resolve(IVoskModel)
            service = VoskAsrService(model)
            return service
        
        container.add_singleton(IAsrService, service_factory)
        
        # Store registration info for later reference
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
