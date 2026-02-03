"""
Model trainer for Scikit-learn NLU.
"""

import re
import pickle
from pathlib import Path
from typing import List, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    Pipeline = None

from ..interfaces import IModelTrainer, IMLPipeline


class SklearnModelTrainer(IModelTrainer):
    """
    Scikit-learn model trainer.
    
    Creates and trains TF-IDF + Naive Bayes pipelines for intent classification.
    """
    
    def __init__(self):
        """Initialize trainer."""
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed")
    
    @staticmethod
    def _preprocess_text(text: str) -> str:
        """
        Preprocess text for training/inference.
        
        Args:
            text: Raw input text
            
        Returns:
            Preprocessed text
        """
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    def train(self, data: List[Tuple[str, str]]) -> Pipeline:
        """
        Train a model on the given data.
        
        Args:
            data: List of (text, label) tuples
            
        Returns:
            Trained scikit-learn pipeline
        """
        if not data:
            raise ValueError("Training data cannot be empty")
        
        # Split data
        texts, labels = zip(*data)
        
        # Create pipeline
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                preprocessor=self._preprocess_text,
                ngram_range=(1, 2),  # Use unigrams and bigrams
                min_df=1,  # Minimum document frequency
                max_df=1.0,  # Maximum document frequency
            )),
            ('classifier', MultinomialNB(
                alpha=0.1  # Laplace smoothing
            ))
        ])
        
        # Train
        pipeline.fit(texts, labels)
        
        return pipeline
    
    def save(self, pipeline: Pipeline, path: str) -> None:
        """
        Save trained pipeline to disk.
        
        Args:
            pipeline: Trained pipeline
            path: Path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump(pipeline, f)
    
    def load(self, path: str) -> Pipeline:
        """
        Load pipeline from disk.
        
        Args:
            path: Path to load from
            
        Returns:
            Loaded pipeline
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        
        with open(path, 'rb') as f:
            return pickle.load(f)


class SklearnPipelineWrapper:
    """
    Wrapper for scikit-learn pipeline to implement IMLPipeline interface.
    """
    
    def __init__(self, pipeline: Pipeline, label_mapping: dict = None):
        """
        Initialize wrapper.
        
        Args:
            pipeline: Scikit-learn pipeline
            label_mapping: Optional mapping from indices to labels
        """
        self._pipeline = pipeline
        self._label_mapping = label_mapping or {}
        self._classes = pipeline.classes_ if hasattr(pipeline, 'classes_') else []
    
    def predict(self, texts: List[str]) -> List[str]:
        """Predict intents for given texts."""
        return self._pipeline.predict(texts).tolist()
    
    def predict_proba(self, texts: List[str]) -> List[List[float]]:
        """Get prediction probabilities."""
        return self._pipeline.predict_proba(texts).tolist()
    
    def predict_single(self, text: str) -> Tuple[str, float]:
        """
        Predict intent for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (predicted_label, confidence)
        """
        prediction = self._pipeline.predict([text])[0]
        probabilities = self._pipeline.predict_proba([text])[0]
        confidence = max(probabilities)
        
        return prediction, confidence
