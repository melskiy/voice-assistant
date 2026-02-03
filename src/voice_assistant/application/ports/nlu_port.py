"""
NLU Port - Interface for Natural Language Understanding services.

User goal: Extract intent and entities from text.
Success guarantee: Returns intent classification or indicates uncertainty.
Side effects: None (stateless operation).
"""
from typing import Any, Protocol

from ..dto.intent_dto import IntentDTO


class NLUPort(Protocol):
    """
    Port interface for NLU (Natural Language Understanding) services.
    
    Infrastructure adapters must implement this interface to provide
    intent classification and entity extraction capabilities.
    """
    
    async def classify_intent(self, text: str) -> IntentDTO:
        """
        Classify intent from text.
        
        Args:
            text: Input text to classify
            
        Returns:
            Intent classification with confidence
            
        Raises:
            NLUError: If classification fails
        """
        ...
    
    async def extract_entities(self, text: str) -> dict[str, Any]:
        """
        Extract entities from text.
        
        Args:
            text: Input text to process
            
        Returns:
            Dictionary of extracted entities
        """
        ...
    
    async def process_text(self, text: str) -> IntentDTO:
        """
        Process text to extract both intent and entities.
        
        Args:
            text: Input text to process
            
        Returns:
            Intent with extracted entities
        """
        ...
    
    def is_available(self) -> bool:
        """
        Check if NLU service is available.
        
        Returns:
            True if service is ready to accept requests
        """
        ...
