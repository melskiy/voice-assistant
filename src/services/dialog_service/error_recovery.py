"""
Error recovery and clarification module for Dialog Service.

Provides enhanced error handling, clarifying questions, and help responses
for low ASR confidence and failed NLU extraction scenarios.

Requirements: 5.5, 9.1, 9.2
"""
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


class ErrorCategory(Enum):
    """Categories of errors for targeted recovery"""
    LOW_CONFIDENCE_ASR = "low_confidence_asr"
    LOW_CONFIDENCE_NLU = "low_confidence_nlu"
    MISSING_ENTITY = "missing_entity"
    UNKNOWN_INTENT = "unknown_intent"
    RECOVERY_TIMEOUT = "recovery_timeout"
    SYSTEM_ERROR = "system_error"


@dataclass
class ErrorRecoveryPrompt:
    """Represents an error recovery prompt with metadata"""
    category: ErrorCategory
    base_prompt: str
    context_prompts: Dict[str, str] = field(default_factory=dict)
    max_retries: int = 3
    fallback_message: str = "Давайте начнём сначала. Чем могу помочь?"


class ErrorRecoveryPrompts:
    """Collection of error recovery prompts for various scenarios"""
    
    # Low ASR confidence prompts
    LOW_CONFIDENCE_ASR = ErrorRecoveryPrompt(
        category=ErrorCategory.LOW_CONFIDENCE_ASR,
        base_prompt="Не расслышала. Повторите, пожалуйста.",
        context_prompts={
            "AWAITING_COMMAND": "Не расслышала команду. Повторите, пожалуйста.",
            "COLLECTING_ITEM": "Не расслышала название продукта. Повторите, пожалуйста.",
            "AWAITING_QUANTITY": "Не расслышала количество. Повторите, пожалуйста.",
            "AWAITING_DATE": "Не расслышала дату. Повторите, пожалуйста.",
            "CONFIRMING": "Не расслышала подтверждение. Скажите да или нет.",
        },
        max_retries=3,
        fallback_message="Давайте начнём сначала. Чем могу помочь?"
    )
    
    # Low NLU confidence prompts
    LOW_CONFIDENCE_NLU = ErrorRecoveryPrompt(
        category=ErrorCategory.LOW_CONFIDENCE_NLU,
        base_prompt="Не поняла. Уточните, пожалуйста.",
        context_prompts={
            "AWAITING_COMMAND": "Не поняла команду. Попробуйте сказать иначе.",
            "COLLECTING_ITEM": "Не поняла название продукта. Скажите ещё раз.",
            "AWAITING_QUANTITY": "Не поняла количество. Скажите число словами или цифрами.",
            "AWAITING_DATE": "Не поняла дату. Например: \"завтра\" или \"15 января\".",
            "CONFIRMING": "Не поняла ваш ответ. Подтвердите: да или нет?",
        },
        max_retries=2,
        fallback_message="Давайте начнём сначала. Чем могу помочь?"
    )
    
    # Missing entity prompts
    MISSING_ENTITY = ErrorRecoveryPrompt(
        category=ErrorCategory.MISSING_ENTITY,
        base_prompt="Уточните, пожалуйста.",
        context_prompts={
            "item": "Какой именно продукт вы имеете в виду?",
            "quantity": "Сколько нужно?",
            "date": "На какую дату?",
            "description": "О чём именно напомнить?",
            "reminder_item": "Напомнить о чём?",
        },
        max_retries=3,
        fallback_message="Не могу продолжить без этой информации. Чем ещё могу помочь?"
    )
    
    # Unknown intent prompts
    UNKNOWN_INTENT = ErrorRecoveryPrompt(
        category=ErrorCategory.UNKNOWN_INTENT,
        base_prompt="Извините, не поняла вашу просьбу.",
        context_prompts={
            "AWAITING_COMMAND": "Чем могу помочь? Могу добавить продукты, показать список или создать напоминание.",
            "COLLECTING_ITEM": "Скажите, что добавить в список или убрать из него.",
            "AWAITING_QUANTITY": "Скажите количество или вернитесь к выбору продукта.",
            "AWAITING_DATE": "Назовите дату или отмените действие.",
            "CONFIRMING": "Ответьте да или нет.",
        },
        max_retries=2,
        fallback_message="Давайте начнём сначала. Чем могу помочь?"
    )
    
    # Recovery timeout prompts
    RECOVERY_TIMEOUT = ErrorRecoveryPrompt(
        category=ErrorCategory.RECOVERY_TIMEOUT,
        base_prompt="Нет ответа. Возвращаюсь в начало.",
        context_prompts={
            "AWAITING_COMMAND": "Если нужна помощь, скажите что-нибудь.",
            "COLLECTING_ITEM": "Если хотите добавить что-то в список, скажите название продукта.",
        },
        max_retries=1,
        fallback_message="Нет ответа. Чем могу помочь?"
    )


class HelpMenuResponses:
    """Help menu and fallback responses for the dialog service"""
    
    # Main help message
    MAIN_HELP = """Чем могу помочь? Вот что я умею:
• Добавить продукты в список покупок - скажите "добавь молоко"
• Убрать продукты из списка - скажите "убери хлеб"
• Показать список покупок - скажите "покажи список"
• Создать напоминание - скажите "напомни позвонить маме"
• Показать напоминания - скажите "какие напоминания"

Что бы вы хотели сделать?"""
    
    # Help for shopping list
    SHOPPING_HELP = """Для работы со списком покупок:
• "добавь [продукт]" - добавить продукт в список
• "убери [продукт]" - убрать продукт из списка
• "покажи список" - показать все продукты
• "очисти список" - удалить все продукты

Что добавить в список?"""
    
    # Help for reminders
    REMINDER_HELP = """Для создания напоминаний:
• "напомни [описание]" - создать напоминание
• "напомни [описание] [дата]" - создать напоминание на конкретную дату
• "какие напоминания" - показать все напоминания
• "удали напоминание" - удалить напоминание

О чём напомнить?"""
    
    # Help for confirmation
    CONFIRMATION_HELP = """Пожалуйста, подтвердите:
• Скажите "да" или "нет"
• Или "подтвердить" / "отменить"

Ваш ответ?"""
    
    # Fallback for repeated failures
    FALLBACK_AFTER_FAILURES = """Извините, у нас не получается понять друг друга.
Вот что я умею:
• Добавлять продукты в список
• Показывать список покупок
• Создавать напоминания

Просто скажите, что хотите сделать - и я помогу!"""
    
    # Polite exit
    GOODBYE = """Хорошо, если понадоблюсь - обращайтесь! До свидания!"""
    
    # Error fallback
    ERROR_FALLBACK = "Извините, произошла ошибка. Попробуйте ещё раз или начните сначала."
    
    @classmethod
    def get_help_for_state(cls, state: str, context: Dict[str, str] = None) -> str:
        """Get contextual help based on current state"""
        help_map = {
            "AWAITING_COMMAND": cls.MAIN_HELP,
            "COLLECTING_ITEM": cls.SHOPPING_HELP,
            "AWAITING_QUANTITY": "Скажите количество, например: один, два, три или 1, 2, 3",
            "AWAITING_DATE": cls.REMINDER_HELP,
            "CONFIRMING": cls.CONFIRMATION_HELP,
            "ERROR_RECOVERY": cls.FALLBACK_AFTER_FAILURES,
        }
        
        if context and context.get("intent_type") == "reminder":
            return cls.REMINDER_HELP
        
        return help_map.get(state, cls.MAIN_HELP)


class ErrorRecoveryManager:
    """
    Manages error recovery and clarification for dialog service.
    
    Tracks error patterns, generates contextual recovery prompts,
    and implements progressive fallback strategies.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history: Dict[str, List[Tuple[ErrorCategory, int]]] = {}
        self.prompts = ErrorRecoveryPrompts()
        self.help = HelpMenuResponses()
    
    def categorize_error(
        self,
        confidence: float,
        intent_name: str,
        entities: Dict[str, str],
        current_state: str
    ) -> ErrorCategory:
        """Categorize the type of error for targeted recovery"""
        
        # Low ASR confidence
        if confidence < 0.6:
            return ErrorCategory.LOW_CONFIDENCE_ASR
        
        # Low NLU confidence (medium confidence)
        if confidence < 0.7:
            return ErrorCategory.LOW_CONFIDENCE_NLU
        
        # Missing entities
        if intent_name in ["ADD_SHOPPING_ITEM", "REMOVE_SHOPPING_ITEM"] and not entities.get("item"):
            return ErrorCategory.MISSING_ENTITY
        if intent_name == "CREATE_REMINDER" and not entities.get("description"):
            return ErrorCategory.MISSING_ENTITY
        
        # Unknown intent
        if intent_name in ["UNKNOWN", "NONE", ""]:
            return ErrorCategory.UNKNOWN_INTENT
        
        return ErrorCategory.SYSTEM_ERROR
    
    def get_recovery_prompt(
        self,
        error_category: ErrorCategory,
        current_state: str,
        missing_entity: str = None,
        retry_count: int = 0
    ) -> str:
        """Get an appropriate recovery prompt based on error category and context"""
        
        if error_category == ErrorCategory.LOW_CONFIDENCE_ASR:
            prompt = self._get_context_prompt(
                self.prompts.LOW_CONFIDENCE_ASR,
                current_state
            )
            return self._add_retry_context(prompt, retry_count)
        
        elif error_category == ErrorCategory.LOW_CONFIDENCE_NLU:
            prompt = self._get_context_prompt(
                self.prompts.LOW_CONFIDENCE_NLU,
                current_state
            )
            return self._add_retry_context(prompt, retry_count)
        
        elif error_category == ErrorCategory.MISSING_ENTITY:
            if missing_entity:
                entity_prompts = self.prompts.MISSING_ENTITY.context_prompts
                if missing_entity in entity_prompts:
                    return entity_prompts[missing_entity]
            return self.prompts.MISSING_ENTITY.base_prompt
        
        elif error_category == ErrorCategory.UNKNOWN_INTENT:
            return self._get_context_prompt(
                self.prompts.UNKNOWN_INTENT,
                current_state
            )
        
        else:
            return self.help.ERROR_FALLBACK
    
    def _get_context_prompt(self, error_prompt: ErrorRecoveryPrompt, current_state: str) -> str:
        """Get a context-specific prompt from an error prompt template"""
        if current_state in error_prompt.context_prompts:
            return error_prompt.context_prompts[current_state]
        return error_prompt.base_prompt
    
    def _add_retry_context(self, prompt: str, retry_count: int) -> str:
        """Add context about retry count to help users understand"""
        if retry_count == 0:
            return prompt
        elif retry_count == 1:
            return f"{prompt} Попробуйте говорить чётче."
        elif retry_count == 2:
            return f"{prompt} Пожалуйста, постарайтесь говорить громче и чётче."
        else:
            return self.help.FALLBACK_AFTER_FAILURES
    
    def get_help_response(self, current_state: str = None, context: Dict[str, str] = None) -> str:
        """Get an appropriate help response"""
        if current_state:
            return self.help.get_help_for_state(current_state, context)
        return self.help.MAIN_HELP
    
    def get_fallback_response(self, session_id: str, retry_count: int) -> Tuple[str, str, bool, bool]:
        """Get a fallback response when all recovery attempts fail"""
        self.logger.warning(f"Session {session_id} exceeded retry limit ({retry_count})")
        
        # Reset the conversation
        return (
            self.help.FALLBACK_AFTER_FAILURES,
            "reset_session",
            False,  # requires_confirmation
            True    # session_complete
        )
    
    def should_escalate(
        self,
        error_category: ErrorCategory,
        retry_count: int,
        max_retries: int = 3
    ) -> bool:
        """Determine if we should escalate to a higher level of recovery"""
        if error_category == ErrorCategory.LOW_CONFIDENCE_ASR:
            return retry_count >= max_retries
        elif error_category == ErrorCategory.LOW_CONFIDENCE_NLU:
            return retry_count >= 2
        elif error_category == ErrorCategory.MISSING_ENTITY:
            return retry_count >= max_retries
        elif error_category == ErrorCategory.UNKNOWN_INTENT:
            return retry_count >= 2
        else:
            return retry_count >= 1
    
    def track_error(
        self,
        session_id: str,
        error_category: ErrorCategory,
        confidence: float = None
    ) -> int:
        """Track error occurrence for a session and return current retry count"""
        if session_id not in self.error_history:
            self.error_history[session_id] = []
        
        self.error_history[session_id].append((error_category, confidence if confidence else 0))
        
        # Count recent errors of the same category (last 5)
        recent_errors = [
            (cat, conf) for cat, conf in self.error_history[session_id][-5:]
            if cat == error_category
        ]
        
        return len(recent_errors)
    
    def clear_error_history(self, session_id: str):
        """Clear error history for a session after successful recovery"""
        if session_id in self.error_history:
            del self.error_history[session_id]
    
    def is_error_pattern_detected(self, session_id: str, threshold: int = 5) -> bool:
        """Detect if there are too many consecutive errors"""
        if session_id not in self.error_history:
            return False
        
        return len(self.error_history[session_id]) >= threshold
