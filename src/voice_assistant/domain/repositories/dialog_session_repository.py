"""
Dialog Session Repository interface.

Defines the contract for dialog session persistence.
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..entities.dialog_session import DialogSession


class IDialogSessionRepository(ABC):
    """
    Interface for dialog session repository.
    
    Implementations can use in-memory storage, Redis, PostgreSQL, etc.
    """
    
    @abstractmethod
    async def get_by_id(self, session_id: str) -> Optional[DialogSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            DialogSession or None if not found
        """
        pass
    
    @abstractmethod
    async def save(self, session: DialogSession) -> None:
        """
        Save session.
        
        Args:
            session: DialogSession to save
        """
        pass
    
    @abstractmethod
    async def update(self, session: DialogSession) -> None:
        """
        Update session.
        
        Args:
            session: DialogSession to update
        """
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """
        Delete session.
        
        Args:
            session_id: Session identifier
        """
        pass
