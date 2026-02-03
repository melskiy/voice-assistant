from pydantic import BaseModel
from typing import Any
from datetime import datetime


class IntentDTO(BaseModel):
    """Data transfer object for recognized intents"""
    name: str
    confidence: float
    entities: dict[str, Any] = {}
    extracted_at: datetime = datetime.utcnow()

    @classmethod
    def from_entity(cls, intent) -> 'IntentDTO':
        """Create DTO from domain entity"""
        return cls(
            name=intent.name,
            confidence=intent.confidence.score,
            entities=intent.entities,
            extracted_at=datetime.utcnow()
        )