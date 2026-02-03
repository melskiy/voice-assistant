"""
Scikit-learn based NLU Service implementation.
"""

from typing import Dict, Any, Optional
from pathlib import Path

try:
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    Pipeline = None

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseNluService,
    IntentResult
)
from ..interfaces import ITrainingDataProvider, IModelTrainer
from .model_trainer import SklearnPipelineWrapper


class SklearnNluService(BaseNluService):
    """
    Scikit-learn based NLU service.
    
    Uses TF-IDF and Naive Bayes for intent classification.
    All dependencies are injected via constructor.
    """
    
    def __init__(
        self,
        training_data_provider: ITrainingDataProvider,
        model_trainer: IModelTrainer,
        model_path: Optional[str] = None,
        train_on_init: bool = True
    ):
        """
        Initialize NLU service.
        
        Args:
            training_data_provider: Provider of training data
            model_trainer: Model trainer component
            model_path: Optional path to pre-trained model
            train_on_init: Whether to train on initialization if no model exists
        """
        self._training_data_provider = training_data_provider
        self._model_trainer = model_trainer
        self._model_path = model_path
        self._train_on_init = train_on_init
        self._pipeline_wrapper: Optional[SklearnPipelineWrapper] = None
    
    async def initialize(self) -> None:
        """
        Initialize the service by loading or training the model.
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed")
        
        # Try to load pre-trained model
        if self._model_path and Path(self._model_path).exists():
            pipeline = self._model_trainer.load(self._model_path)
            self._pipeline_wrapper = SklearnPipelineWrapper(pipeline)
        elif self._train_on_init:
            # Train with default data
            await self._train_model()
        else:
            raise RuntimeError("No model available and train_on_init is False")
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._pipeline_wrapper = None
    
    async def _train_model(self) -> None:
        """Train the model with default training data."""
        training_data = self._training_data_provider.get_training_data()
        
        if not training_data:
            raise ValueError("No training data available")
        
        pipeline = self._model_trainer.train(training_data)
        self._pipeline_wrapper = SklearnPipelineWrapper(pipeline)
        
        # Save model if path is specified
        if self._model_path:
            self._model_trainer.save(pipeline, self._model_path)
    
    async def classify_intent(self, text: str) -> IntentResult:
        """
        Classify intent from text using the ML model.
        
        Args:
            text: Input text to classify
            
        Returns:
            IntentResult with intent name and confidence
        """
        if self._pipeline_wrapper is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        # Predict
        intent, confidence = self._pipeline_wrapper.predict_single(text)
        
        # Extract entities (basic implementation)
        entities = await self.extract_entities(text, intent)
        
        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            raw_text=text
        )
    
    async def extract_entities(self, text: str, intent: str = None) -> Dict[str, Any]:
        """
        Extract entities from text.
        
        For sklearn-based NLU, we use simple regex extraction as a fallback.
        
        Args:
            text: Input text
            intent: Optional intent context
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Simple entity extraction based on patterns
        import re
        
        # Extract items (words after action verbs)
        item_patterns = [
            r"(?:добавь|купи|нужен|нужна|возьми|положи|напомни)\s+(\w+)",
            r"(?:add|buy|need|get|remind)\s+(\w+)",
        ]
        
        for pattern in item_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities["item"] = match.group(1)
                break
        
        # Extract dates
        date_patterns = [
            r"(?:завтра|послезавтра|сегодня)",
            r"(?:tomorrow|today)"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities["date"] = match.group(0)
                break
        
        return entities
    
    def is_trained(self) -> bool:
        """Check if the model is trained and ready."""
        return self._pipeline_wrapper is not None
