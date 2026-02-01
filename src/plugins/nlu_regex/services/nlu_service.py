"""
Regex-based NLU Service implementation.

This module implements the INluService interface using regex patterns.
"""

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseNluService,
    IntentResult
)
from ..interfaces import IPatternRepository, IEntityExtractor


class RegexNluService(BaseNluService):
    """
    Regex-based NLU service implementation.
    
    Uses pattern matching for intent classification and entity extraction.
    All dependencies are injected via constructor.
    """
    
    def __init__(
        self,
        pattern_repository: IPatternRepository,
        entity_extractor: IEntityExtractor,
        default_confidence: float = 0.8
    ):
        """
        Initialize NLU service.
        
        Args:
            pattern_repository: Repository of intent patterns
            entity_extractor: Entity extraction component
            default_confidence: Default confidence score for matches
        """
        self._pattern_repository = pattern_repository
        self._entity_extractor = entity_extractor
        self._default_confidence = default_confidence
    
    async def initialize(self) -> None:
        """Initialize the service."""
        # No async initialization needed for regex-based service
        pass
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        pass
    
    async def classify_intent(self, text: str) -> IntentResult:
        """
        Classify intent from text using regex patterns.
        
        Args:
            text: Input text to classify
            
        Returns:
            IntentResult with intent name and confidence
        """
        # Find matching intent
        intent_name = self._pattern_repository.find_matching_intent(text)
        
        if intent_name:
            # Calculate confidence based on match quality
            # Exact matches get higher confidence
            confidence = self._calculate_confidence(text, intent_name)
            
            # Extract entities
            entities = await self.extract_entities(text, intent_name)
            
            return IntentResult(
                intent=intent_name,
                confidence=confidence,
                entities=entities,
                raw_text=text
            )
        else:
            # No match found
            return IntentResult(
                intent="UNKNOWN",
                confidence=0.0,
                entities={},
                raw_text=text
            )
    
    async def extract_entities(self, text: str, intent: str = None) -> dict:
        """
        Extract entities from text.
        
        Args:
            text: Input text
            intent: Optional intent context
            
        Returns:
            Dictionary of extracted entities
        """
        return self._entity_extractor.extract(text, intent)
    
    def _calculate_confidence(self, text: str, intent: str) -> float:
        """
        Calculate confidence score for a match.
        
        Args:
            text: Input text
            intent: Matched intent
            
        Returns:
            Confidence score between 0 and 1
        """
        # Get patterns for the intent
        patterns = self._pattern_repository.get_patterns(intent)
        
        if not patterns:
            return self._default_confidence * 0.5
        
        pattern = patterns[0]
        
        # Higher confidence for shorter, more specific matches
        # and for matches at the beginning of the text
        confidence = self._default_confidence
        
        # Boost confidence for matches at the start
        text_lower = text.lower()
        for p in pattern.patterns:
            p_clean = p.replace(r".*", "").replace(r"\s+", " ").lower()
            if text_lower.startswith(p_clean[:10]):
                confidence = min(0.95, confidence + 0.1)
                break
        
        # Reduce confidence for very long texts (more chance of false positive)
        if len(text) > 100:
            confidence *= 0.9
        
        return confidence
