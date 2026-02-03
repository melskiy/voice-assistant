from pydantic import BaseModel
from typing import Any
from ..value_objects.confidence import ConfidenceScore


class Intent(BaseModel):
    """Domain entity representing a recognized user intent"""
    name: str
    confidence: ConfidenceScore
    entities: dict[str, Any]

    def is_reliable(self) -> bool:
        """Check if the intent recognition is reliable"""
        return self.confidence.is_reliable()

    def is_uncertain(self) -> bool:
        """Check if the intent recognition is uncertain"""
        return self.confidence.is_uncertain()

    def has_entity(self, entity_name: str) -> bool:
        """Check if the intent has a specific entity"""
        return entity_name in self.entities

    def get_entity(self, entity_name: str, default: Any = None) -> Any:
        """Get an entity value or default if not present"""
        return self.entities.get(entity_name, default)

    @classmethod
    def create(
        cls,
        name: str,
        confidence_score: float,
        entities: dict[str, Any] | None = None,
        threshold: float = 0.6
    ) -> 'Intent':
        """Factory method to create an intent"""
        if entities is None:
            entities = {}
        
        confidence = ConfidenceScore(score=confidence_score, threshold=threshold)
        return cls(name=name, confidence=confidence, entities=entities)