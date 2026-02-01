from pydantic import BaseModel, validator


class ConfidenceScore(BaseModel):
    """Value object for confidence scores"""
    score: float
    threshold: float = 0.6  # Default minimum acceptable confidence

    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v

    @validator('threshold')
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Threshold must be between 0.0 and 1.0')
        return v

    def is_reliable(self) -> bool:
        """Check if the confidence score is above threshold"""
        return self.score >= self.threshold

    def is_uncertain(self) -> bool:
        """Check if the confidence score is below threshold"""
        return self.score < self.threshold

    def __str__(self) -> str:
        return f"{self.score:.2f}"

    def __float__(self) -> float:
        return self.score