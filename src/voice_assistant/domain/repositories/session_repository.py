from abc import ABC
from typing import Optional
from uuid import UUID
from ..entities.session import Session


class ISessionRepository(ABC):
    """Abstract interface for session repository"""
    
    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Get session by ID"""
        raise NotImplementedError
    
    async def save(self, session: Session) -> None:
        """Save session"""
        raise NotImplementedError
    
    async def update(self, session: Session) -> None:
        """Update existing session"""
        raise NotImplementedError
    
    async def delete(self, session_id: UUID) -> None:
        """Delete session"""
        raise NotImplementedError