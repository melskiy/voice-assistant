"""
Dialog Use Cases for Dialog Service.

User goal: Process dialog interactions and manage conversation state.
Success guarantee: Returns appropriate response based on intent and state.
Side effects: Updates session state, may modify shopping/reminder lists.
"""
from typing import Dict, Any, Tuple
from datetime import datetime

from ...domain.entities.dialog_session import DialogSession, DialogState, DialogTurn
from ...domain.repositories.dialog_session_repository import IDialogSessionRepository
from ...domain.value_objects.dialog_response import DialogResponse


class ProcessIntentUseCase:
    """
    Use case for processing intents in dialog context.
    
    Handles intent processing based on current dialog state.
    """
    
    def __init__(
        self,
        session_repo: IDialogSessionRepository,
        error_recovery_service=None
    ):
        self.session_repo = session_repo
        self.error_recovery = error_recovery_service
    
    async def execute(
        self,
        session_id: str,
        intent_name: str,
        entities: Dict[str, str],
        confidence: float,
        raw_text: str
    ) -> Tuple[str, str, bool, bool]:
        """
        Process intent and return response.
        
        Args:
            session_id: Session identifier
            intent_name: Recognized intent name
            entities: Extracted entities
            confidence: Confidence score
            raw_text: Original user text
            
        Returns:
            Tuple of (response_text, action, requires_confirmation, session_complete)
        """
        # Get or create session
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            session = DialogSession(
                session_id=session_id,
                current_state=DialogState.AWAITING_COMMAND
            )
            await self.session_repo.save(session)
        
        # Update context
        session.last_user_input = raw_text
        session.current_intent = intent_name
        for key, value in entities.items():
            session.context_variables[key] = value
        
        # Check confidence and error recovery
        if self.error_recovery:
            error_category = self.error_recovery.categorize_error(
                confidence, intent_name, entities, session.current_state.value
            )
            retry_count = self.error_recovery.track_error(
                session_id, error_category, confidence
            )
            
            if self.error_recovery.should_escalate(error_category, retry_count):
                self.error_recovery.clear_error_history(session_id)
                session.retry_count = 0
                session.transition_to(DialogState.AWAITING_COMMAND)
                await self.session_repo.update(session)
                return self.error_recovery.get_fallback_response(session_id, retry_count)
            
            if confidence < 0.6:
                session.retry_count = retry_count
                await self.session_repo.update(session)
                response_text = self.error_recovery.get_recovery_prompt(
                    error_category,
                    session.current_state.value,
                    retry_count=retry_count
                )
                return response_text, "error_recovery", False, False
            
            if confidence < 0.7:
                session.transition_to(DialogState.CONFIRMING)
                await self.session_repo.update(session)
                return f"Вы сказали: '{raw_text}'. Это так?", "request_confirmation", True, False
            
            # Clear error history on success
            self.error_recovery.clear_error_history(session_id)
        
        session.retry_count = 0
        
        # Handle based on state
        if session.current_state == DialogState.AWAITING_COMMAND:
            result = await self._handle_awaiting_command(session, intent_name, entities)
        elif session.current_state == DialogState.COLLECTING_ITEM:
            result = await self._handle_collecting_item(session, intent_name, entities, raw_text)
        elif session.current_state == DialogState.AWAITING_QUANTITY:
            result = await self._handle_awaiting_quantity(session, intent_name, entities)
        elif session.current_state == DialogState.AWAITING_DATE:
            result = await self._handle_awaiting_date(session, intent_name, entities)
        elif session.current_state == DialogState.CONFIRMING:
            result = await self._handle_confirming(session, intent_name, entities)
        elif session.current_state == DialogState.ERROR_RECOVERY:
            result = await self._handle_error_recovery(session, intent_name, entities)
        else:
            result = await self._handle_awaiting_command(session, intent_name, entities)
        
        await self.session_repo.update(session)
        return result
    
    async def _handle_awaiting_command(
        self,
        session: DialogSession,
        intent_name: str,
        entities: Dict[str, str]
    ) -> Tuple[str, str, bool, bool]:
        """Handle intents when waiting for a command."""
        if intent_name == "ADD_SHOPPING_ITEM":
            item = entities.get('item', '')
            
            if item:
                session.add_shopping_item(item)
                return f"Добавила {item} в список покупок. Что ещё?", "add_item_success", False, False
            else:
                session.transition_to(DialogState.COLLECTING_ITEM)
                return "Какой продукт хотите добавить в список покупок?", "request_item", False, False
        
        elif intent_name == "REMOVE_SHOPPING_ITEM":
            item = entities.get('item', '')
            
            if item:
                if session.remove_shopping_item(item):
                    return f"Убрала {item} из списка покупок. Что ещё?", "remove_item_success", False, False
                else:
                    return f"{item} нет в списке покупок. Что ещё?", "item_not_found", False, False
            else:
                session.transition_to(DialogState.COLLECTING_ITEM)
                return "Какой продукт нужно убрать из списка покупок?", "request_item_to_remove", False, False
        
        elif intent_name == "GET_SHOPPING_LIST":
            if session.shopping_list:
                items_str = ", ".join(session.shopping_list)
                return f"В вашем списке покупок: {items_str}", "show_list", False, False
            else:
                return "Ваш список покупок пуст", "show_empty_list", False, False
        
        elif intent_name == "CREATE_REMINDER":
            description = entities.get('description', '')
            
            if description:
                session.add_reminder(description)
                return f"Создала напоминание: {description}. Что ещё?", "create_reminder_success", False, False
            else:
                session.transition_to(DialogState.COLLECTING_ITEM)
                return "О чём напомнить?", "request_reminder_description", False, False
        
        elif intent_name == "GET_REMINDERS":
            if session.reminder_list:
                descriptions = [r['description'] for r in session.reminder_list]
                reminders_str = ", ".join(descriptions)
                return f"У вас запланированы напоминания: {reminders_str}", "show_reminders", False, False
            else:
                return "У вас нет активных напоминаний", "show_no_reminders", False, False
        
        elif intent_name == "HELP":
            return (
                "Я могу помочь вам с:\n"
                "- Добавлением продуктов в список покупок\n"
                "- Созданием напоминаний\n"
                "- Просмотром списка покупок\n"
                "Что вы хотите сделать?"
            ), "show_help", False, False
        
        elif intent_name in ["CONFIRM_YES", "CONFIRM_NO"]:
            if intent_name == "CONFIRM_YES":
                return "Хорошо, подтверждено. Что ещё?", "confirmed_outside_context", False, False
            else:
                return "Хорошо, действие отменено. Что ещё?", "cancelled_outside_context", False, False
        
        else:
            return (
                "Чем могу помочь? Могу добавить продукты в список покупок "
                "или создать напоминание."
            ), "help_prompt", False, False
    
    async def _handle_collecting_item(
        self,
        session: DialogSession,
        intent_name: str,
        entities: Dict[str, str],
        raw_text: str
    ) -> Tuple[str, str, bool, bool]:
        """Handle intents when collecting an item."""
        if intent_name in ["CONFIRM_YES", "CONFIRM_NO"]:
            session.transition_to(DialogState.AWAITING_COMMAND)
            if intent_name == "CONFIRM_YES":
                return "Хорошо, подтверждено. Что ещё?", "confirmed", False, False
            else:
                return "Хорошо, действие отменено. Что ещё?", "cancelled", False, False
        
        if intent_name == "HELP":
            return (
                "Назовите продукт или описание напоминания. "
                "Например: 'молоко' или 'купить хлеб'"
            ), "show_help", False, False
        
        # Extract item from entities or raw text
        item = entities.get('item', '')
        if not item and intent_name == "ADD_SHOPPING_ITEM":
            # Simple extraction from raw text
            import re
            raw_text_lower = raw_text.lower()
            for word in ['добавь', 'добавить', 'купить', 'положить', 'в', 'список', 'покупок', 'нужно']:
                raw_text_lower = raw_text_lower.replace(word, '')
            potential_items = re.findall(r'\b[а-яё]+\b', raw_text_lower)
            if potential_items:
                item = ' '.join(potential_items)
        
        if item:
            if session.current_intent == "ADD_SHOPPING_ITEM":
                session.add_shopping_item(item)
                session.transition_to(DialogState.AWAITING_COMMAND)
                return f"Добавила {item} в список покупок. Что ещё?", "add_item_success", False, False
            elif session.current_intent == "REMOVE_SHOPPING_ITEM":
                if session.remove_shopping_item(item):
                    session.transition_to(DialogState.AWAITING_COMMAND)
                    return f"Убрала {item} из списка покупок. Что ещё?", "remove_item_success", False, False
                else:
                    session.transition_to(DialogState.AWAITING_COMMAND)
                    return f"{item} нет в списке покупок. Что ещё?", "item_not_found", False, False
            elif session.current_intent == "CREATE_REMINDER":
                session.add_reminder(item)
                session.transition_to(DialogState.AWAITING_COMMAND)
                return f"Создала напоминание: {item}. Что ещё?", "create_reminder_success", False, False
            else:
                session.transition_to(DialogState.AWAITING_COMMAND)
                return f"Добавила {item} в список покупок. Что ещё?", "add_item_fallback", False, False
        else:
            if session.context_variables.get("intent_type") == "reminder":
                return "О чём именно напомнить?", "request_reminder_again", False, False
            return "Пожалуйста, назовите продукт или описание напоминания", "request_item_again", False, False
    
    async def _handle_awaiting_quantity(
        self,
        session: DialogSession,
        intent_name: str,
        entities: Dict[str, str]
    ) -> Tuple[str, str, bool, bool]:
        """Handle intents when awaiting a quantity."""
        session.transition_to(DialogState.AWAITING_COMMAND)
        return (
            "Извините, пока не поддерживаю указание количества. Что ещё?"
        ), "quantity_not_supported", False, False
    
    async def _handle_awaiting_date(
        self,
        session: DialogSession,
        intent_name: str,
        entities: Dict[str, str]
    ) -> Tuple[str, str, bool, bool]:
        """Handle intents when awaiting a date."""
        session.transition_to(DialogState.AWAITING_COMMAND)
        return (
            "Извините, пока не поддерживаю указание даты. Что ещё?"
        ), "date_not_supported", False, False
    
    async def _handle_confirming(
        self,
        session: DialogSession,
        intent_name: str,
        entities: Dict[str, str]
    ) -> Tuple[str, str, bool, bool]:
        """Handle intents when confirming an action."""
        session.transition_to(DialogState.AWAITING_COMMAND)
        if intent_name == "CONFIRM_YES":
            return "Действие подтверждено. Что ещё?", "confirmed", False, False
        elif intent_name == "CONFIRM_NO":
            return "Действие отменено. Что ещё?", "cancelled", False, False
        elif intent_name == "HELP":
            return "Скажите 'да' для подтверждения или 'нет' для отмены.", "show_help", False, False
        else:
            return "Подтвердите действие или отмените. Да или нет?", "request_confirmation", True, False
    
    async def _handle_error_recovery(
        self,
        session: DialogSession,
        intent_name: str,
        entities: Dict[str, str]
    ) -> Tuple[str, str, bool, bool]:
        """Handle intents during error recovery."""
        session.transition_to(DialogState.AWAITING_COMMAND)
        session.retry_count = 0
        return "Давайте начнём сначала. Чем могу помочь?", "reset_after_error", False, False


class HandleConfirmationUseCase:
    """Use case for handling confirmation responses."""
    
    def __init__(self, session_repo: IDialogSessionRepository):
        self.session_repo = session_repo
    
    async def execute(
        self,
        session_id: str,
        response: str
    ) -> Tuple[str, str, bool, bool]:
        """
        Handle confirmation response.
        
        Args:
            session_id: Session identifier
            response: User response text
            
        Returns:
            Tuple of (response_text, action, requires_confirmation, session_complete)
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return "Сессия не найдена", "error", False, False
        
        response_lower = response.lower()
        
        if any(word in response_lower for word in ["да", "ага", "верно", "правильно", "угу", "yes", "yep"]):
            session.transition_to(DialogState.AWAITING_COMMAND)
            await self.session_repo.update(session)
            return "Подтверждено. Что ещё?", "confirmed", False, False
        elif any(word in response_lower for word in ["нет", "не", "отмена", "cancel", "не того"]):
            session.transition_to(DialogState.AWAITING_COMMAND)
            await self.session_repo.update(session)
            return "Отменено. Что ещё?", "cancelled", False, False
        else:
            return "Пожалуйста, скажите да или нет", "request_clear_confirmation", True, False


class GetDialogStateUseCase:
    """Use case for getting dialog state."""
    
    def __init__(self, session_repo: IDialogSessionRepository):
        self.session_repo = session_repo
    
    async def execute(self, session_id: str) -> DialogSession:
        """
        Get dialog state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            DialogSession
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            session = DialogSession(
                session_id=session_id,
                current_state=DialogState.AWAITING_COMMAND
            )
            await self.session_repo.save(session)
        return session


class ResetDialogUseCase:
    """Use case for resetting dialog session."""
    
    def __init__(self, session_repo: IDialogSessionRepository):
        self.session_repo = session_repo
    
    async def execute(self, session_id: str) -> bool:
        """
        Reset dialog session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        session = await self.session_repo.get_by_id(session_id)
        if session:
            session.reset()
            await self.session_repo.update(session)
        return True
