"""
Interfaces for Regex NLU plugin.

This module defines the contracts that the Regex NLU plugin implements.
"""

from typing import Protocol, Dict, Any, List, runtime_checkable


@runtime_checkable
class IIntentPattern(Protocol):
    """Interface for intent pattern definition."""
    
    @property
    def intent_name(self) -> str:
        """Get the intent name this pattern matches."""
        ...
    
    @property
    def patterns(self) -> List[str]:
        """Get list of regex patterns."""
        ...
    
    def matches(self, text: str) -> bool:
        """Check if text matches any pattern."""
        ...


@runtime_checkable
class IEntityExtractor(Protocol):
    """Interface for entity extractor."""
    
    def extract(self, text: str, intent: str = None) -> Dict[str, Any]:
        """
        Extract entities from text.
        
        Args:
            text: Input text
            intent: Optional intent context for extraction
            
        Returns:
            Dictionary of extracted entities
        """
        ...


@runtime_checkable
class IPatternRepository(Protocol):
    """Interface for pattern repository."""
    
    def get_patterns(self, intent: str = None) -> List[IIntentPattern]:
        """
        Get patterns, optionally filtered by intent.
        
        Args:
            intent: Optional intent name to filter by
            
        Returns:
            List of intent patterns
        """
        ...
    
    def add_pattern(self, pattern: IIntentPattern) -> None:
        """Add a new pattern to the repository."""
        ...
