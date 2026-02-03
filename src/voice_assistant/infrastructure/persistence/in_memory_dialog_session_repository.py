"""
In-memory implementation of Dialog Session Repository.

Used for development and testing. For production, use Redis or PostgreSQL.
"""
from typing import Optional, Dict

from ...domain.entities.dialog_session import DialogSession
from ...domain.repositories.dialog_session_repository import IDialogSessionRepository


class InMemoryDialogSessionRepository(IDialogSessionRepository):
    """
    In-memory repository for dialog sessions.
    
    Stores sessions in a dictionary. Not persistent!
    """
    
    def __init__(self):
        self._sessions: Dict[str, DialogSession] = {}
    
    async def get_by_id(self, session_id: str) -> Optional[DialogSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    async def save(self, session: DialogSession) -> None:
        """Save session."""
        self._sessions[session.session_id] = session
    
    async def update(self, session: DialogSession) -> None:
        """Update session."""
        self._sessions[session.session_id] = session
    
    async def delete(self, session_id: str) -> None:
        """Delete session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        self._sessions.clear()
    
    def get_all_sessions(self) -> Dict[str, DialogSession]:
        """Get all sessions (for debugging)."""
        return self._sessions.copy()
