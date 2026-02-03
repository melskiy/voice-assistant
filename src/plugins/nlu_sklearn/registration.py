"""
Scikit-learn NLU Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    INluService
)
from ..interfaces import ITrainingDataProvider, IModelTrainer
from .services.training_data import DefaultTrainingDataProvider
from .services.model_trainer import SklearnModelTrainer
from .services.nlu_service import SklearnNluService


class SklearnNluPluginRegistration(IPluginRegistration):
    """
    Registration class for Scikit-learn NLU plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="nlu.sklearn",
            name="Scikit-learn NLU",
            version="1.0.0",
            description="ML-based natural language understanding using scikit-learn",
            author="Voice Assistant Team",
            dependencies=["scikit-learn"]
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
                "language": {
                    "type": "string",
                    "default": "ru",
                    "description": "Language code for training data (ru, en)"
                },
                "model_path": {
                    "type": "string",
                    "description": "Path to save/load trained model"
                },
                "train_on_init": {
                    "type": "boolean",
                    "default": True,
                    "description": "Train model on initialization if no saved model exists"
                }
            },
            "required": []
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if scikit-learn is available.
        
        Returns:
            True if scikit-learn is installed
        """
        try:
            import sklearn
            return True
        except ImportError:
            return False
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register Scikit-learn NLU dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Extract configuration
        language = config.get("language", "ru")
        model_path = config.get("model_path")
        train_on_init = config.get("train_on_init", True)
        
        # Register configuration as named instance
        container.add_instance(config, name="nlu_sklearn_config")
        
        # Register training data provider as singleton
        def data_provider_factory(c: Container) -> ITrainingDataProvider:
            return DefaultTrainingDataProvider(language=language)
        
        container.add_singleton(ITrainingDataProvider, data_provider_factory)
        
        # Register model trainer as singleton
        def trainer_factory(c: Container) -> IModelTrainer:
            return SklearnModelTrainer()
        
        container.add_singleton(IModelTrainer, trainer_factory)
        
        # Register NLU service as singleton with lazy initialization
        async def service_factory(c: Container) -> INluService:
            data_provider = c.resolve(ITrainingDataProvider)
            trainer = c.resolve(IModelTrainer)
            
            service = SklearnNluService(
                training_data_provider=data_provider,
                model_trainer=trainer,
                model_path=model_path,
                train_on_init=train_on_init
            )
            
            # Initialize (train or load model)
            await service.initialize()
            
            return service
        
        container.add_singleton(INluService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
