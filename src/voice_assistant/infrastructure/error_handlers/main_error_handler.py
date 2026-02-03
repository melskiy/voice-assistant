from enum import Enum
from typing import Any
from voice_assistant.domain.entities.session import Session, DialogState


class ErrorType(Enum):
    ASR_LOW_CONFIDENCE = "asr_low_confidence"
    ASR_NO_SPEECH = "asr_no_speech"
    ASR_AUDIO_QUALITY = "asr_audio_quality"
    ASR_SERVICE_UNAVAILABLE = "asr_service_unavailable"
    NLU_UNKNOWN_INTENT = "nlu_unknown_intent"
    NLU_MISSING_ENTITIES = "nlu_missing_entities"
    NLU_AMBIGUOUS_INPUT = "nlu_ambiguous_input"
    NLU_SERVICE_UNAVAILABLE = "nlu_service_unavailable"
    DIALOG_STATE_TRANSITION_ERROR = "dialog_state_transition_error"
    SERVICE_COMMUNICATION_ERROR = "service_communication_error"
    SYSTEM_ERROR = "system_error"


class MainErrorHandler:
    """Main error handler that coordinates all error handling strategies"""
    
    def __init__(self, max_retry_attempts: int = 3):
        self.max_retry_attempts = max_retry_attempts
    
    async def handle_error(
        self, 
        error_type: ErrorType, 
        session: Session, 
        error_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle different types of errors and return recovery strategy"""
        if error_type == ErrorType.ASR_LOW_CONFIDENCE:
            return await self._handle_asr_low_confidence(session, error_context)
        elif error_type == ErrorType.ASR_NO_SPEECH:
            return await self._handle_asr_no_speech(session, error_context)
        elif error_type == ErrorType.ASR_AUDIO_QUALITY:
            return await self._handle_asr_audio_quality(session, error_context)
        elif error_type == ErrorType.ASR_SERVICE_UNAVAILABLE:
            return await self._handle_asr_service_unavailable(session, error_context)
        elif error_type == ErrorType.NLU_UNKNOWN_INTENT:
            return await self._handle_nlu_unknown_intent(session, error_context)
        elif error_type == ErrorType.NLU_MISSING_ENTITIES:
            return await self._handle_nlu_missing_entities(session, error_context)
        elif error_type == ErrorType.NLU_AMBIGUOUS_INPUT:
            return await self._handle_nlu_ambiguous_input(session, error_context)
        elif error_type == ErrorType.NLU_SERVICE_UNAVAILABLE:
            return await self._handle_nlu_service_unavailable(session, error_context)
        elif error_type == ErrorType.DIALOG_STATE_TRANSITION_ERROR:
            return await self._handle_dialog_state_transition_error(session, error_context)
        elif error_type == ErrorType.SERVICE_COMMUNICATION_ERROR:
            return await self._handle_service_communication_error(session, error_context)
        elif error_type == ErrorType.SYSTEM_ERROR:
            return await self._handle_system_error(session, error_context)
        else:
            # Default handling for unknown errors
            return await self._handle_unknown_error(session, error_context)
    
    async def _handle_asr_low_confidence(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle low confidence transcription"""
        current_retry_count = session.context_data.get('retry_count', 0)
        
        if current_retry_count >= self.max_retry_attempts:
            return self._handle_max_retries_exceeded(session)
        
        # Determine appropriate recovery response based on context
        recovery_messages = {
            DialogState.AWAITING_COMMAND: "Я не расслышала. Повторите команду.",
            DialogState.COLLECTING_ITEM: "Не расслышала название продукта. Повторите.",
            DialogState.AWAITING_DATE: "Не расслышала дату. Повторите дату, например, 'завтра'.",
            DialogState.AWAITING_LOCATION: "Не расслышала место. Повторите место.",
            DialogState.CONFIRMING: "Не расслышала подтверждение. Скажите 'да' или 'нет'.",
            DialogState.ERROR_RECOVERY: "Давайте начнём сначала. Какую команду вы хотите выполнить?"
        }
        
        return {
            'should_retry': True,
            'retry_count': current_retry_count + 1,
            'prompt_message': recovery_messages.get(session.state, "Повторите, пожалуйста."),
            'next_state': session.state,
            'context_updates': {'retry_count': current_retry_count + 1, 'failed_field': 'transcription'}
        }
    
    async def _handle_asr_no_speech(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle when no speech is detected in audio chunk"""
        current_retry_count = session.context_data.get('retry_count', 0)
        
        if current_retry_count >= self.max_retry_attempts:
            return self._handle_max_retries_exceeded(session)
        
        return {
            'should_retry': True,
            'retry_count': current_retry_count + 1,
            'prompt_message': "Я вас не слышу. Пожалуйста, говорите четче в микрофон.",
            'next_state': session.state,
            'context_updates': {'retry_count': current_retry_count + 1, 'failed_field': 'audio_input'}
        }
    
    async def _handle_asr_audio_quality(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle poor audio quality"""
        current_retry_count = session.context_data.get('retry_count', 0)
        
        if current_retry_count >= self.max_retry_attempts:
            return self._handle_max_retries_exceeded(session)
        
        return {
            'should_retry': True,
            'retry_count': current_retry_count + 1,
            'prompt_message': "Качество звука плохое. Пожалуйста, повторите.",
            'next_state': session.state,
            'context_updates': {'retry_count': current_retry_count + 1, 'failed_field': 'audio_quality'}
        }
    
    async def _handle_asr_service_unavailable(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle ASR service unavailability"""
        return {
            'should_retry': False,
            'retry_count': 0,
            'prompt_message': "Сейчас я не могу распознать речь. Пожалуйста, повторите позже.",
            'next_state': DialogState.ERROR_RECOVERY,
            'context_updates': {'error_type': ErrorType.ASR_SERVICE_UNAVAILABLE.value}
        }
    
    async def _handle_nlu_unknown_intent(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle when intent cannot be determined"""
        # Try to extract any recognizable entities from ambiguous text
        text = error_context.get('text', '') if error_context else ''
        
        recovery_messages = {
            DialogState.AWAITING_COMMAND: f"Я не совсем поняла команду '{text}'. Можете сказать по-другому? Вы можете попросить меня добавить продукт в список покупок или создать напоминание.",
            DialogState.COLLECTING_ITEM: f"Не поняла название продукта '{text}'. Можете повторить название продукта?",
            DialogState.AWAITING_DATE: f"Не поняла дату '{text}'. Скажите дату, например, 'завтра' или '15 марта'.",
            DialogState.AWAITING_LOCATION: f"Не поняла место '{text}'. Назовите место еще раз.",
            DialogState.CONFIRMING: f"Не поняла ваш ответ '{text}'. Пожалуйста, скажите 'да' или 'нет'.",
            DialogState.ERROR_RECOVERY: f"Я не поняла '{text}'. Давайте вернемся к началу. Какую команду вы хотите выполнить?"
        }
        
        return {
            'should_retry': True,
            'prompt_message': recovery_messages.get(session.state, f"Не поняла '{text}'. Повторите, пожалуйста."),
            'next_state': session.state,
            'context_updates': {
                'last_failed_input': text,
                'recovered_entities': {}  # Would extract entities in real implementation
            }
        }
    
    async def _handle_nlu_missing_entities(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle when required entities are missing for an intent"""
        required_entities = error_context.get('required_entities', []) if error_context else []
        missing_str = ", ".join(required_entities) if required_entities else "информация"
        
        recovery_messages = {
            DialogState.AWAITING_COMMAND: f"Для этой команды мне нужно знать {missing_str}.",
            DialogState.COLLECTING_ITEM: f"Чтобы добавить продукт, мне нужно знать {missing_str}.",
            DialogState.AWAITING_DATE: f"Мне нужно знать {missing_str} для напоминания.",
            DialogState.AWAITING_LOCATION: f"Мне нужно знать {missing_str}.",
            DialogState.CONFIRMING: f"Мне нужно знать {missing_str} для подтверждения.",
            DialogState.ERROR_RECOVERY: f"Нужна дополнительная информация: {missing_str}."
        }
        
        return {
            'should_retry': True,
            'prompt_message': recovery_messages.get(session.state, f"Мне нужно знать {missing_str}."),
            'next_state': session.state,
            'context_updates': {
                'required_entities': required_entities,
                'partial_intent': error_context.get('partial_intent', {}) if error_context else {}
            }
        }
    
    async def _handle_nlu_ambiguous_input(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle when input could match multiple intents"""
        # Present options to user for clarification
        options_msg = "Уточните, пожалуйста: "
        possible_intents = error_context.get('possible_intents', []) if error_context else []
        
        for i, intent in enumerate(possible_intents[:3]):  # Show first 3 options
            if i > 0:
                options_msg += " или "
            options_msg += intent.get('description', 'неизвестный вариант')
        
        return {
            'should_retry': True,
            'prompt_message': f"{options_msg}",
            'next_state': DialogState.AWAITING_COMMAND,
            'context_updates': {
                'ambiguous_input': error_context.get('text', '') if error_context else '',
                'possible_intents': possible_intents
            }
        }
    
    async def _handle_nlu_service_unavailable(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle NLU service unavailability"""
        return {
            'should_retry': False,
            'prompt_message': "Сейчас я не могу понять команду. Пожалуйста, повторите позже.",
            'next_state': DialogState.ERROR_RECOVERY,
            'context_updates': {'error_type': ErrorType.NLU_SERVICE_UNAVAILABLE.value}
        }
    
    async def _handle_dialog_state_transition_error(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle errors during state transitions"""
        current_retry_count = session.context_data.get('error_recovery_attempts', 0)
        
        if current_retry_count >= self.max_retry_attempts:
            return self._handle_max_retries_exceeded(session)
        
        return {
            'should_retry': True,
            'retry_count': current_retry_count + 1,
            'prompt_message': "Произошла ошибка. Давайте начем с начала. Как я могу вам помочь?",
            'next_state': DialogState.AWAITING_COMMAND,
            'context_updates': {
                'error_recovery_attempts': current_retry_count + 1,
                'last_error': error_context
            }
        }
    
    async def _handle_service_communication_error(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle errors in service communication"""
        service_name = error_context.get('service_name', 'неизвестный') if error_context else 'неизвестный'
        
        return {
            'should_retry': False,
            'prompt_message': f"Сервис {service_name} временно недоступен. Пожалуйста, повторите позже.",
            'next_state': DialogState.ERROR_RECOVERY,
            'context_updates': {
                'service_error': {
                    'service': service_name,
                    'error': error_context.get('error', 'неизвестная ошибка') if error_context else 'неизвестная ошибка',
                }
            }
        }
    
    async def _handle_system_error(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle general system errors"""
        error_msg = error_context.get('error', 'неизвестная ошибка') if error_context else 'неизвестная ошибка'
        
        # Log the error
        import traceback
        traceback.print_exc()
        
        return {
            'should_retry': False,
            'prompt_message': "Произошла системная ошибка. Давайте начем сначала. Как я могу вам помочь?",
            'next_state': DialogState.AWAITING_COMMAND,
            'context_updates': {
                'system_error': {
                    'type': error_context.get('type', 'неизвестный') if error_context else 'неизвестный',
                    'message': error_msg,
                },
                'reset_context': True
            }
        }
    
    async def _handle_unknown_error(
        self, 
        session: Session, 
        error_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Handle unknown error types"""
        return {
            'should_retry': False,
            'prompt_message': "Произошла неизвестная ошибка. Давайте начем сначала. Как я могу вам помочь?",
            'next_state': DialogState.AWAITING_COMMAND,
            'context_updates': {
                'unknown_error': error_context or {},
                'reset_context': True
            }
        }
    
    def _handle_max_retries_exceeded(self, session: Session) -> dict[str, Any]:
        """Handle when maximum retry attempts are exceeded"""
        return {
            'should_retry': False,
            'retry_count': 0,
            'prompt_message': "Мы несколько раз не смогли понять друг друга. Давайте начем сначала. Как я могу вам помочь?",
            'next_state': DialogState.AWAITING_COMMAND,
            'context_updates': {
                'retry_count': 0, 
                'reset_context': True
            }
        }
    
    async def reset_session_errors(self, session: Session) -> Session:
        """Reset error-related context in session"""
        # Remove error-related context data
        error_keys = [
            'retry_count', 'error_recovery_attempts', 'last_error', 
            'service_error', 'system_error', 'error_type'
        ]
        
        for key in error_keys:
            session.context_data.pop(key, None)
        
        # Reset to safe state if in error state
        if session.state == DialogState.ERROR_RECOVERY:
            session.state = DialogState.AWAITING_COMMAND
        
        return session