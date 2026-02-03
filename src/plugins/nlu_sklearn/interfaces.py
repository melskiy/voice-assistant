"""
Interfaces for Scikit-learn NLU plugin.
"""

from typing import Protocol, Dict, Any, List, runtime_checkable


@runtime_checkable
class IMLPipeline(Protocol):
    """Interface for ML pipeline."""
    
    def predict(self, texts: List[str]) -> List[str]:
        """Predict intents for given texts."""
        ...
    
    def predict_proba(self, texts: List[str]) -> List[List[float]]:
        """Get prediction probabilities."""
        ...


@runtime_checkable
class ITrainingDataProvider(Protocol):
    """Interface for training data provider."""
    
    def get_training_data(self) -> List[tuple]:
        """
        Get training data as list of (text, label) tuples.
        
        Returns:
            List of training samples
        """
        ...
    
    def get_intent_labels(self) -> List[str]:
        """Get list of all intent labels."""
        ...


@runtime_checkable
class IModelTrainer(Protocol):
    """Interface for model trainer."""
    
    def train(self, data: List[tuple]) -> IMLPipeline:
        """
        Train a model on the given data.
        
        Args:
            data: List of (text, label) tuples
            
        Returns:
            Trained pipeline
        """
        ...
    
    def save(self, pipeline: IMLPipeline, path: str) -> None:
        """Save trained pipeline to disk."""
        ...
    
    def load(self, path: str) -> IMLPipeline:
        """Load pipeline from disk."""
        ...
