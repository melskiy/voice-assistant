"""
Dialog Engine entity for managing dialog state transitions and business rules.

Business concept: Core domain entity that encapsulates dialog state machine logic,
state transition rules, and response generation based on current context.
Constraints:
    - State transitions must follow valid paths
    - Error recovery after 3 failed attempts
    - Context data is immutable for each state
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from ..entities.session import Session, DialogState
from ..entities.intent import Intent


@dataclass
class DialogEngine:
    """
    Domain entity for dialog state management.
    
    Encapsulates business rules for:
    - State transitions
    - Retry counting for error recovery
    - Response generation based on state
    """
    session: Session
    max_retry_attempts: int = 3
    _retry_count: int = field(default=0, repr=False)
    
    # Valid state transitions mapping
    VALID_TRANSITIONS: dict = field(default_factory=lambda: {
        DialogState.AWAITING_COMMAND: [
            DialogState.COLLECTING_ITEM,
            DialogState.AWAITING_DATE,
            DialogState.CONFIRMING,
            DialogState.ERROR_RECOVERY
        ],
        DialogState.COLLECTING_ITEM: [
            DialogState.AWAITING_COMMAND,
            DialogState.CONFIRMING,
            DialogState.ERROR_RECOVERY
        ],
        DialogState.AWAITING_DATE: [
            DialogState.AWAITING_COMMAND,
            DialogState.CONFIRMING,
            DialogState.ERROR_RECOVERY
        ],
        DialogState.AWAITING_LOCATION: [
            DialogState.AWAITING_COMMAND,
            DialogState.CONFIRMING,
            DialogState.ERROR_RECOVERY
        ],
        DialogState.CONFIRMING: [
            DialogState.AWAITING_COMMAND,
            DialogState.ERROR_RECOVERY
        ],
        DialogState.ERROR_RECOVERY: [
            DialogState.AWAITING_COMMAND,
            DialogState.COLLECTING_ITEM,
            DialogState.AWAITING_DATE
        ],
        DialogState.COMPLETED: [DialogState.AWAITING_COMMAND]
    }, repr=False)
    
    def can_transition_to(self, new_state: DialogState) -> bool:
        """
        Business rule: Check if transition to new state is valid.
        
        Args:
            new_state: Target state for transition
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_states = self.VALID_TRANSITIONS.get(self.session.state, [])
        return new_state in valid_states or new_state == self.session.state
    
    def transition_to(
        self, 
        new_state: DialogState, 
        context_updates: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Business rule: Transition to new state with context updates.
        
        Args:
            new_state: Target state
            context_updates: Optional context data to merge
            
        Raises:
            ValueError: If transition is not valid
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {self.session.state} to {new_state}"
            )
        
        # Reset retry count on successful state change (not error recovery)
        if new_state != DialogState.ERROR_RECOVERY:
            self._retry_count = 0
        
        self.session.update_state(new_state, context_updates or {})
    
    def record_failed_attempt(self) -> bool:
        """
        Business rule: Record a failed understanding attempt.
        
        Returns:
            True if should continue retry, False if max attempts reached
        """
        self._retry_count += 1
        return self._retry_count < self.max_retry_attempts
    
    def should_reset_dialog(self) -> bool:
        """
        Business rule: Check if dialog should be reset due to max retries.
        
        Returns:
            True if max retry attempts exceeded
        """
        return self._retry_count >= self.max_retry_attempts
    
    def get_response_for_state(self, intent_name: Optional[str] = None) -> str:
        """
        Business rule: Get appropriate response text for current state.
        
        Args:
            intent_name: Optional detected intent name for context
            
        Returns:
            Response text in Russian
        """
        responses = {
            DialogState.AWAITING_COMMAND: (
                "Я могу помочь вам с добавлением товаров в список покупок "
                "или созданием напоминаний. Что вы хотите сделать?"
            ),
            DialogState.COLLECTING_ITEM: "Какой товар вы хотите добавить?",
            DialogState.AWAITING_DATE: (
                "Когда вам напомнить? "
                "Например: сегодня, завтра, через час"
            ),
            DialogState.AWAITING_LOCATION: "Где это нужно сделать?",
            DialogState.CONFIRMING: "Пожалуйста, подтвердите. Скажите да или нет.",
            DialogState.ERROR_RECOVERY: self._get_error_recovery_response(),
            DialogState.COMPLETED: "Что-нибудь ещё?"
        }
        
        return responses.get(
            self.session.state, 
            "Что вы хотите сделать?"
        )
    
    def _get_error_recovery_response(self) -> str:
        """Generate context-aware error recovery response."""
        if self.should_reset_dialog():
            return "Давайте начнём сначала. Чем могу помочь?"
        
        # Context-specific retry prompt
        previous_state = self.session.context_data.get("previous_state")
        if previous_state == DialogState.AWAITING_DATE.value:
            return "Не расслышала дату. Повторите, например: завтра в 15:00"
        elif previous_state == DialogState.COLLECTING_ITEM.value:
            return "Не расслышала название товара. Повторите, пожалуйста."
        
        return "Не расслышала. Повторите, пожалуйста."
    
    def handle_intent(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """
        Business rule: Process intent and determine next state and response.
        
        Args:
            intent: Recognized intent
            text: Original user text
            
        Returns:
            Tuple of (next_state, response_text)
        """
        # Check intent confidence
        if intent.is_uncertain():
            if not self.record_failed_attempt():
                # Max retries reached, reset dialog
                self.transition_to(DialogState.ERROR_RECOVERY)
                return DialogState.AWAITING_COMMAND, self.get_response_for_state()
            
            self.transition_to(
                DialogState.ERROR_RECOVERY,
                {"previous_state": self.session.state.value}
            )
            return DialogState.ERROR_RECOVERY, self.get_response_for_state()
        
        # Handle based on current state and intent
        handler = self._get_state_handler()
        return handler(intent, text)
    
    def _get_state_handler(self):
        """Get appropriate handler for current state."""
        handlers = {
            DialogState.AWAITING_COMMAND: self._handle_awaiting_command,
            DialogState.COLLECTING_ITEM: self._handle_collecting_item,
            DialogState.AWAITING_DATE: self._handle_awaiting_date,
            DialogState.AWAITING_LOCATION: self._handle_awaiting_location,
            DialogState.CONFIRMING: self._handle_confirming,
            DialogState.ERROR_RECOVERY: self._handle_error_recovery,
        }
        return handlers.get(
            self.session.state, 
            self._handle_default
        )
    
    def _handle_awaiting_command(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Handle intent when awaiting command."""
        if intent.name == "ADD_SHOPPING_ITEM":
            item_name = intent.get_entity("item", "")
            if item_name:
                self.transition_to(
                    DialogState.AWAITING_COMMAND,
                    {"item_to_add": item_name}
                )
                return (
                    DialogState.AWAITING_COMMAND,
                    f"Добавила {item_name} в ваш список покупок. Что ещё?"
                )
            else:
                self.transition_to(
                    DialogState.COLLECTING_ITEM,
                    {"partial_item": ""}
                )
                return (
                    DialogState.COLLECTING_ITEM,
                    "Какой товар вы хотите добавить в список покупок?"
                )
        
        elif intent.name == "GET_SHOPPING_LIST":
            # Return to same state, response handled by caller
            return (
                DialogState.AWAITING_COMMAND,
                "LIST_REQUEST"  # Signal to caller to fetch list
            )
        
        elif intent.name == "CREATE_REMINDER":
            description = intent.get_entity("description", "напоминание")
            self.transition_to(DialogState.AWAITING_COMMAND)
            return (
                DialogState.AWAITING_COMMAND,
                f"Хорошо, я запомнила: {description}. Что ещё?"
            )
        
        else:
            return (
                DialogState.AWAITING_COMMAND,
                self.get_response_for_state(intent.name)
            )
    
    def _handle_collecting_item(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Handle intent when collecting item information."""
        context = self.session.context_data
        partial_item = context.get("partial_item", text.strip())
        
        if intent.name == "CONFIRM_YES":
            item_name = partial_item or text.strip()
            self.transition_to(DialogState.AWAITING_COMMAND, {})
            return (
                DialogState.AWAITING_COMMAND,
                f"Добавила {item_name} в ваш список покупок. Что ещё?"
            )
        
        elif intent.name == "CONFIRM_NO":
            self.transition_to(DialogState.AWAITING_COMMAND, {})
            return (
                DialogState.AWAITING_COMMAND,
                "Хорошо, не добавляю. Что ещё могу для вас сделать?"
            )
        
        else:
            # Treat text as item name
            item_name = text.strip()
            self.transition_to(DialogState.AWAITING_COMMAND, {})
            return (
                DialogState.AWAITING_COMMAND,
                f"Добавила {item_name} в ваш список покупок. Что ещё?"
            )
    
    def _handle_awaiting_date(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Handle intent when awaiting date information."""
        self.transition_to(DialogState.AWAITING_COMMAND, {})
        return (
            DialogState.AWAITING_COMMAND,
            "Дата установлена. Что ещё?"
        )
    
    def _handle_awaiting_location(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Handle intent when awaiting location information."""
        self.transition_to(DialogState.AWAITING_COMMAND, {})
        return (
            DialogState.AWAITING_COMMAND,
            "Место установлено. Что ещё?"
        )
    
    def _handle_confirming(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Handle intent in confirmation state."""
        if intent.name == "CONFIRM_YES":
            self.transition_to(DialogState.AWAITING_COMMAND, {})
            return (
                DialogState.AWAITING_COMMAND,
                "Подтверждено. Что ещё?"
            )
        elif intent.name == "CONFIRM_NO":
            self.transition_to(DialogState.AWAITING_COMMAND, {})
            return (
                DialogState.AWAITING_COMMAND,
                "Отменено. Что ещё?"
            )
        else:
            return (
                DialogState.CONFIRMING,
                "Пожалуйста, скажите да или нет."
            )
    
    def _handle_error_recovery(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Handle intent in error recovery state."""
        # After error recovery, always go back to awaiting command
        self.transition_to(DialogState.AWAITING_COMMAND, {})
        return (
            DialogState.AWAITING_COMMAND,
            "Давайте начнём сначала. Что вы хотите сделать?"
        )
    
    def _handle_default(
        self, 
        intent: Intent, 
        text: str
    ) -> tuple[DialogState, str]:
        """Default handler for unknown states."""
        self.transition_to(DialogState.AWAITING_COMMAND, {})
        return (
            DialogState.AWAITING_COMMAND,
            "Что вы хотите сделать?"
        )
