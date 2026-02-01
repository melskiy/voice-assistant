"""
Scikit-learn NLU Plugin.

This plugin provides ML-based natural language understanding using scikit-learn.

Usage:
    from rodi import Container
    from plugins.nlu_sklearn import SklearnNluPluginRegistration
    
    container = Container()
    config = {"language": "ru", "train_on_init": True}
    SklearnNluPluginRegistration.register(container, config)
    
    # Resolve and use the service
    nlu_service = container.resolve(INluService)
    result = await nlu_service.classify_intent("добавь молоко в список")
"""

from .registration import SklearnNluPluginRegistration
from .interfaces import IMLPipeline, ITrainingDataProvider, IModelTrainer
from .services.training_data import DefaultTrainingDataProvider
from .services.model_trainer import SklearnModelTrainer, SklearnPipelineWrapper
from .services.nlu_service import SklearnNluService

__all__ = [
    # Registration
    "SklearnNluPluginRegistration",
    # Interfaces
    "IMLPipeline",
    "ITrainingDataProvider",
    "IModelTrainer",
    # Services
    "DefaultTrainingDataProvider",
    "SklearnModelTrainer",
    "SklearnPipelineWrapper",
    "SklearnNluService",
]
