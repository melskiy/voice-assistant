"""
Dialog Session entity for Dialog Service.

Business concept: Represents a dialog session with state management,
conversation history, and shopping/reminder lists.
Constraints:
    - Session has unique ID
    - State transitions follow valid paths
    - History is limited to prevent memory issues
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import uuid


class DialogState(Enum):
    """Enumeration of possible dialog states"""
    AWAITING_COMMAND = "awaiting_command"
    COLLECTING_ITEM = "collecting_item"
    AWAITING_QUANTITY = "awaiting_quantity"
    AWAITING_DATE = "awaiting_date"
    CONFIRMING = "confirming"
    ERROR_RECOVERY = "error_recovery"
    COMPLETED = "completed"


@dataclass
class DialogTurn:
    """
    Value object representing a single turn in the conversation.
    
    Attributes:
        user_input: Text from user
        system_response: Response from system
        intent_name: Recognized intent
        timestamp_ms: Timestamp in milliseconds
        confidence: Confidence score
        entities: Extracted entities
    """
    user_input: str
    system_response: str
    intent_name: str
    timestamp_ms: int
    confidence: float
    entities: Dict[str, str] = field(default_factory=dict)


@dataclass
class DialogSession:
    """
    Domain entity representing a dialog session.
    
    Business rules:
    - Session has unique ID
    - State transitions must be valid
    - History is limited to prevent memory issues
    """
    session_id: str
    current_state: DialogState
    current_intent: str = ""
    conversation_history: List[DialogTurn] = field(default_factory=list)
    pending_confirmations: List[str] = field(default_factory=list)
    context_variables: Dict[str, str] = field(default_factory=dict)
    shopping_list: List[str] = field(default_factory=list)
    reminder_list: List[Dict[str, Any]] = field(default_factory=list)
    last_user_input: str = ""
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    # Business rule: max history size
    MAX_HISTORY_SIZE: int = 50
    
    def add_turn(self, turn: DialogTurn) -> None:
        """
        Business rule: Add turn to history with size limit.
        
        Args:
            turn: Dialog turn to add
        """
        self.conversation_history.append(turn)
        
        # Business rule: Limit history size
        if len(self.conversation_history) > self.MAX_HISTORY_SIZE:
            self.conversation_history = self.conversation_history[-self.MAX_HISTORY_SIZE:]
    
    def transition_to(self, new_state: DialogState) -> None:
        """
        Business rule: Transition to new state if valid.
        
        Args:
            new_state: Target state
            
        Raises:
            ValueError: If transition is invalid
        """
        if not self._is_valid_transition(new_state):
            raise ValueError(
                f"Invalid transition from {self.current_state} to {new_state}"
            )
        self.current_state = new_state
    
    def _is_valid_transition(self, new_state: DialogState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            DialogState.AWAITING_COMMAND: [
                DialogState.COLLECTING_ITEM,
                DialogState.AWAITING_QUANTITY,
                DialogState.AWAITING_DATE,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY,
                DialogState.COMPLETED
            ],
            DialogState.COLLECTING_ITEM: [
                DialogState.AWAITING_COMMAND,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.AWAITING_QUANTITY: [
                DialogState.AWAITING_COMMAND,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.AWAITING_DATE: [
                DialogState.AWAITING_COMMAND,
                DialogState.CONFIRMING,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.CONFIRMING: [
                DialogState.AWAITING_COMMAND,
                DialogState.ERROR_RECOVERY,
                DialogState.COMPLETED
            ],
            DialogState.ERROR_RECOVERY: [
                DialogState.AWAITING_COMMAND,
                DialogState.COLLECTING_ITEM,
                DialogState.ERROR_RECOVERY
            ],
            DialogState.COMPLETED: [
                DialogState.AWAITING_COMMAND
            ]
        }
        
        valid_states = valid_transitions.get(self.current_state, [])
        return new_state in valid_states or new_state == self.current_state
    
    def add_shopping_item(self, item: str) -> None:
        """Add item to shopping list."""
        self.shopping_list.append(item)
    
    def remove_shopping_item(self, item: str) -> bool:
        """
        Remove item from shopping list.
        
        Returns:
            True if item was found and removed
        """
        if item in self.shopping_list:
            self.shopping_list.remove(item)
            return True
        return False
    
    def add_reminder(self, description: str) -> str:
        """
        Add reminder to list.
        
        Returns:
            ID of created reminder
        """
        reminder_id = str(uuid.uuid4())
        self.reminder_list.append({
            "id": reminder_id,
            "description": description,
            "created_at": datetime.now()
        })
        return reminder_id
    
    def reset(self) -> None:
        """Reset session to initial state."""
        self.current_state = DialogState.AWAITING_COMMAND
        self.current_intent = ""
        self.conversation_history.clear()
        self.pending_confirmations.clear()
        self.context_variables.clear()
        self.shopping_list.clear()
        self.reminder_list.clear()
        self.last_user_input = ""
        self.retry_count = 0
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """
        Check if session has expired.
        
        Args:
            timeout_minutes: Timeout in minutes
            
        Returns:
            True if session expired
        """
        elapsed = (datetime.now() - self.created_at).total_seconds() / 60
        return elapsed > timeout_minutes
