from pydantic import BaseModel
from typing import Any


class CommandResult(BaseModel):
    """Result of command execution"""
    success: bool
    message: str
    data: Any | None = None
    error_code: str | None = None

    @classmethod
    def success(cls, message: str, data: Any | None = None) -> 'CommandResult':
        return cls(success=True, message=message, data=data)

    @classmethod
    def failure(cls, message: str, error_code: str | None = None) -> 'CommandResult':
        return cls(success=False, message=message, error_code=error_code)