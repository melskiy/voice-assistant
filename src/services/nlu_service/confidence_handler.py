"""
Confidence-based processing logic for NLU service.
Implements requirements 4.3 and 4.4 for confidence threshold handling.
"""
from typing import Optional
import logging

from voice_assistant.application.dto.intent_dto import IntentDTO

logger = logging.getLogger(__name__)


class ConfidenceHandler:
    """Handles confidence-based processing logic for intent classification"""
    
    def __init__(self, threshold: float = 0.7):
        """
        Initialize confidence handler with threshold.
        
        Args:
            threshold: Minimum confidence threshold (0.0 to 1.0). Default is 0.7
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.threshold = threshold
        logger.info(f"Confidence handler initialized with threshold {threshold}")
    
    def categorize_confidence(self, confidence: float) -> str:
        """
        Categorize confidence level.
        
        Args:
            confidence: Confidence score between 0.0 and 1.0
            
        Returns:
            str: One of 'HIGH', 'MEDIUM', 'LOW'
        """
        if confidence >= self.threshold:
            return 'HIGH'
        elif confidence >= self.threshold - 0.2:  # Medium range
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def is_high_confidence(self, confidence: float) -> bool:
        """
        Check if confidence is above threshold.
        
        Args:
            confidence: Confidence score between 0.0 and 1.0
            
        Returns:
            bool: True if confidence is high enough
        """
        return confidence >= self.threshold
    
    def is_low_confidence(self, confidence: float) -> bool:
        """
        Check if confidence is below acceptable threshold.
        
        Args:
            confidence: Confidence score between 0.0 and 1.0
            
        Returns:
            bool: True if confidence is too low
        """
        return confidence < (self.threshold - 0.2)  # Lower threshold for low confidence marking
    
    def process_intent(self, intent_dto: IntentDTO) -> tuple[IntentDTO, str]:
        """
        Process intent with confidence-based logic.
        
        Args:
            intent_dto: Input intent with confidence score
            
        Returns:
            tuple: (processed_intent, confidence_category)
        """
        category = self.categorize_confidence(intent_dto.confidence)
        
        # Log confidence level for monitoring
        logger.debug(f"Intent '{intent_dto.name}' has {category} confidence: {intent_dto.confidence:.2f}")
        
        # Mark intent if confidence is particularly low
        if self.is_low_confidence(intent_dto.confidence):
            # Add a flag to indicate low confidence for downstream processing
            if not hasattr(intent_dto, 'low_confidence_flag'):
                # We'll add this as metadata in entities
                if 'low_confidence' not in intent_dto.entities:
                    intent_dto.entities['low_confidence'] = True
        
        return intent_dto, category
    
    def get_routing_decision(self, intent_dto: IntentDTO) -> str:
        """
        Get routing decision based on confidence level.
        
        Args:
            intent_dto: Input intent with confidence score
            
        Returns:
            str: Routing decision ('direct', 'verification_needed', 'error_recovery')
        """
        if self.is_high_confidence(intent_dto.confidence):
            return 'direct'  # High confidence, proceed directly
        elif self.categorize_confidence(intent_dto.confidence) == 'MEDIUM':
            return 'verification_needed'  # Medium confidence, ask for verification
        else:
            return 'error_recovery'  # Low confidence, trigger error recovery