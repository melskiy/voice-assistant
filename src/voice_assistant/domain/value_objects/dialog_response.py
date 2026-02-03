"""
Dialog Response value object for representing system responses.

Business concept: Immutable value object representing a response from the
dialog system with metadata about confidence and state.
Constraints:
    - Immutable after creation
    - Confidence threshold for uncertainty detection
    - Response text is required
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from ..entities.session import DialogState


@dataclass(frozen=True)
class DialogResponse:
    """
    Value object representing a dialog system response.
    
    Attributes:
        text: Response text to speak
        state: Current dialog state
        confidence: Confidence score (0.0 to 1.0)
        intent_name: Detected intent name (optional)
        session_id: Associated session ID
        context_data: Additional context
        created_at: Creation timestamp
    """
    text: str
    state: DialogState
    confidence: float = 1.0
    intent_name: Optional[str] = None
    session_id: Optional[UUID] = None
    context_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Business rule: threshold for uncertain responses
    UNCERTAINTY_THRESHOLD: float = field(default=0.6, repr=False)
    
    def __post_init__(self):
        """Validate response after creation."""
        if not self.text:
            raise ValueError("Response text cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
    
    def is_uncertain(self) -> bool:
        """
        Business rule: Check if response confidence is below threshold.
        
        Returns:
            True if confidence is below uncertainty threshold
        """
        return self.confidence < self.UNCERTAINTY_THRESHOLD
    
    def is_final(self) -> bool:
        """
        Check if this is a final response for the interaction.
        
        Returns:
            True if state indicates completion
        """
        return self.state in [
            DialogState.COMPLETED,
            DialogState.ERROR_RECOVERY
        ]
    
    def requires_user_input(self) -> bool:
        """
        Check if response requires user input.
        
        Returns:
            True if waiting for user response
        """
        return self.state in [
            DialogState.AWAITING_COMMAND,
            DialogState.COLLECTING_ITEM,
            DialogState.AWAITING_DATE,
            DialogState.AWAITING_LOCATION,
            DialogState.CONFIRMING
        ]
    
    def with_updated_text(self, new_text: str) -> 'DialogResponse':
        """
        Create a new response with updated text (immutable update).
        
        Args:
            new_text: New response text
            
        Returns:
            New DialogResponse instance
        """
        return DialogResponse(
            text=new_text,
            state=self.state,
            confidence=self.confidence,
            intent_name=self.intent_name,
            session_id=self.session_id,
            context_data=self.context_data.copy(),
            created_at=self.created_at
        )
    
    def with_context(self, key: str, value: Any) -> 'DialogResponse':
        """
        Create a new response with additional context (immutable update).
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            New DialogResponse instance
        """
        new_context = self.context_data.copy()
        new_context[key] = value
        
        return DialogResponse(
            text=self.text,
            state=self.state,
            confidence=self.confidence,
            intent_name=self.intent_name,
            session_id=self.session_id,
            context_data=new_context,
            created_at=self.created_at
        )
    
    @classmethod
    def error_response(
        cls,
        message: str = "Произошла ошибка. Повторите, пожалуйста.",
        session_id: Optional[UUID] = None
    ) -> 'DialogResponse':
        """
        Factory method for error responses.
        
        Args:
            message: Error message
            session_id: Associated session ID
            
        Returns:
            Error DialogResponse
        """
        return cls(
            text=message,
            state=DialogState.ERROR_RECOVERY,
            confidence=0.0,
            session_id=session_id
        )
    
    @classmethod
    def success_response(
        cls,
        message: str,
        state: DialogState = DialogState.AWAITING_COMMAND,
        session_id: Optional[UUID] = None
    ) -> 'DialogResponse':
        """
        Factory method for success responses.
        
        Args:
            message: Success message
            state: Next dialog state
            session_id: Associated session ID
            
        Returns:
            Success DialogResponse
        """
        return cls(
            text=message,
            state=state,
            confidence=1.0,
            session_id=session_id
        )
