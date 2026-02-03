"""
Manage Dialog State Use Case.

User goal: Manage dialog state transitions and context.
Success guarantee: State transitions follow valid paths.
Side effects: Updates session state in repository.
"""
from uuid import UUID
from typing import Any

from ...domain.entities.session import Session, DialogState
from ...domain.entities.dialog_engine import DialogEngine
from ...domain.entities.intent import Intent
from ...domain.repositories.session_repository import ISessionRepository
from ...domain.value_objects.dialog_response import DialogResponse


class ManageDialogState:
    """
    Use case for managing dialog state.
    
    Encapsulates state transition logic and session persistence.
    """
    
    def __init__(self, session_repo: ISessionRepository):
        self.session_repo = session_repo
    
    async def transition_to(
        self,
        session_id: UUID,
        new_state: DialogState,
        context_updates: dict[str, Any] | None = None
    ) -> DialogResponse:
        """
        Transition session to new state.
        
        Args:
            session_id: Session identifier
            new_state: Target state
            context_updates: Optional context data
            
        Returns:
            Dialog response for new state
        """
        session = await self.session_repo.get_by_id(session_id)
        
        if not session:
            return DialogResponse.error_response(
                message="Сессия не найдена",
                session_id=session_id
            )
        
        dialog_engine = DialogEngine(session)
        
        try:
            dialog_engine.transition_to(new_state, context_updates)
            await self.session_repo.update(session)
            
            return DialogResponse(
                text=dialog_engine.get_response_for_state(),
                state=new_state,
                session_id=session_id
            )
        except ValueError as e:
            return DialogResponse.error_response(
                message=f"Недопустимый переход состояния: {e}",
                session_id=session_id
            )
    
    async def process_intent(
        self,
        session_id: UUID,
        intent: Intent,
        text: str
    ) -> DialogResponse:
        """
        Process intent and update state accordingly.
        
        Args:
            session_id: Session identifier
            intent: Recognized intent
            text: Original user text
            
        Returns:
            Dialog response
        """
        session = await self.session_repo.get_by_id(session_id)
        
        if not session:
            return DialogResponse.error_response(
                message="Сессия не найдена",
                session_id=session_id
            )
        
        dialog_engine = DialogEngine(session)
        next_state, response_text = dialog_engine.handle_intent(intent, text)
        
        await self.session_repo.update(session)
        
        return DialogResponse(
            text=response_text,
            state=next_state,
            confidence=intent.confidence.score,
            intent_name=intent.name,
            session_id=session_id
        )
    
    async def reset_dialog(self, session_id: UUID) -> DialogResponse:
        """
        Reset dialog to initial state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dialog response
        """
        return await self.transition_to(
            session_id,
            DialogState.AWAITING_COMMAND,
            {}
        )
    
    async def get_current_state(self, session_id: UUID) -> DialogState | None:
        """
        Get current dialog state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current state or None if session not found
        """
        session = await self.session_repo.get_by_id(session_id)
        return session.state if session else None
