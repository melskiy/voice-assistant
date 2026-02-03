from enum import Enum


class Priority(str, Enum):
    """Enum for priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

    def __str__(self) -> str:
        return self.value