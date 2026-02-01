from typing import Dict, Any
from uuid import UUID
from voice_assistant.domain.entities.session import Session, DialogState
from voice_assistant.domain.entities.intent import Intent
from voice_assistant.application.dto.intent_dto import IntentDTO
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.application.dto.session_dto import SessionDTO
from voice_assistant.application.commands.add_shopping_item_command import AddShoppingItemCommand
from voice_assistant.application.commands.create_reminder_command import CreateReminderCommand
from voice_assistant.application.dto.command_result import CommandResult
from voice_assistant.domain.repositories.session_repository import ISessionRepository
from voice_assistant.domain.repositories.shopping_repository import IShoppingRepository
from voice_assistant.domain.repositories.reminder_repository import IReminderRepository
from voice_assistant.application.services.plugin_service import PluginService
from voice_assistant.domain.value_objects.audio_chunk import AudioChunk


class VoiceDialogOrchestrator:
    """Enhanced voice dialog orchestrator with plugin support"""
    
    def __init__(
        self,
        session_repo: ISessionRepository,
        shopping_repo: IShoppingRepository,
        reminder_repo: IReminderRepository,
        command_bus,
        query_bus,
        plugin_service: PluginService
    ):
        self.session_repo = session_repo
        self.shopping_repo = shopping_repo
        self.reminder_repo = reminder_repo
        self.command_bus = command_bus
        self.query_bus = query_bus
        self.plugin_service = plugin_service
    
    async def process_audio_chunk(self, session_id: UUID, audio_chunk: AudioChunk) -> str:
        """Process incoming audio chunk and return TTS response"""
        try:
            # Transcribe audio using ASR plugin
            transcription = await self.plugin_service.transcribe_audio(audio_chunk)
            
            if not transcription or not transcription.is_final:
                # Return empty response for partial transcriptions
                return ""
            
            # Classify intent from transcription using NLU plugin
            intent_dto = await self.plugin_service.classify_intent(transcription.text)
            
            if not intent_dto:
                return "Извините, не удалось распознать команду. Повторите, пожалуйста."
            
            # Process based on current session state and detected intent
            response = await self._handle_by_state_and_intent(
                session_id, intent_dto, transcription.text
            )
            
            return response
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
            return "Извините, произошла ошибка. Повторите, пожалуйста."
    
    async def _handle_by_state_and_intent(self, session_id: UUID, intent_dto: IntentDTO, text: str) -> str:
        """Handle the interaction based on current state and detected intent"""
        # Get current session
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            # Create new session if doesn't exist
            from voice_assistant.domain.value_objects.phone_number import PhoneNumber
            session = Session.create(PhoneNumber(number="+1234567890"))
            await self.session_repo.save(session)
        
        state_handlers = {
            DialogState.AWAITING_COMMAND: self._handle_awaiting_command,
            DialogState.COLLECTING_ITEM: self._handle_collecting_item,
            DialogState.AWAITING_DATE: self._handle_awaiting_date,
            DialogState.AWAITING_LOCATION: self._handle_awaiting_location,
            DialogState.CONFIRMING: self._handle_confirming,
            DialogState.ERROR_RECOVERY: self._handle_error_recovery,
        }
        
        handler = state_handlers.get(session.state, self._handle_default)
        return await handler(session, intent_dto, text)
    
    async def _handle_awaiting_command(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Handle when awaiting a command"""
        if intent_dto.name == "ADD_SHOPPING_ITEM":
            # Move to collecting item state
            item_name = intent_dto.entities.get("item", "")
            
            if item_name:
                # Item was mentioned, confirm it
                # For now, just add it directly
                command = AddShoppingItemCommand(
                    session_id=session.id,
                    item_name=item_name
                )
                
                # In a real implementation, we'd use the command bus
                # For now, we'll simulate the command execution
                result = await self._execute_add_shopping_item(command)
                
                # Update session state
                session.update_state(DialogState.AWAITING_COMMAND)
                await self.session_repo.update(session)
                
                return f"Добавила {item_name} в ваш список покупок. Что ещё?"
            else:
                # Need to collect item name
                session.update_state(DialogState.COLLECTING_ITEM, {"partial_item": ""})
                await self.session_repo.update(session)
                return "Какой товар вы хотите добавить в список покупок?"
        
        elif intent_dto.name == "GET_SHOPPING_LIST":
            # Return shopping list
            shopping_list = await self.shopping_repo.get_by_session(session.id)
            if shopping_list and shopping_list.items:
                items = [item.name for item in shopping_list.items]
                item_str = ", ".join(items)
                return f"Ваш список покупок: {item_str}"
            else:
                return "Ваш список покупок пуст."
        
        elif intent_dto.name == "CREATE_REMINDER":
            # Create reminder
            description = intent_dto.entities.get("description", "напоминание")
            
            # For now, just acknowledge
            session.update_state(DialogState.AWAITING_COMMAND)
            await self.session_repo.update(session)
            
            return f"Хорошо, я запомнила: {description}. Что ещё?"
        
        else:
            # Unknown intent
            return "Я могу помочь вам с добавлением товаров в список покупок или созданием напоминаний. Что вы хотите сделать?"
    
    async def _handle_collecting_item(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Handle when collecting item information"""
        context = session.context_data
        partial_item = context.get("partial_item", text.strip())
        
        if intent_dto.name == "CONFIRM_YES":
            # Confirm the item
            command = AddShoppingItemCommand(
                session_id=session.id,
                item_name=partial_item
            )
            
            result = await self._execute_add_shopping_item(command)
            
            # Return to awaiting command state
            session.update_state(DialogState.AWAITING_COMMAND, {})
            await self.session_repo.update(session)
            
            return f"Добавила {partial_item} в ваш список покупок. Что ещё?"
        elif intent_dto.name == "CONFIRM_NO":
            # Cancel the action
            session.update_state(DialogState.AWAITING_COMMAND, {})
            await self.session_repo.update(session)
            return "Хорошо, не добавляю. Что ещё могу для вас сделать?"
        else:
            # Treat text as item name
            command = AddShoppingItemCommand(
                session_id=session.id,
                item_name=text.strip()
            )
            
            result = await self._execute_add_shopping_item(command)
            
            # Return to awaiting command state
            session.update_state(DialogState.AWAITING_COMMAND, {})
            await self.session_repo.update(session)
            
            return f"Добавила {text.strip()} в ваш список покупок. Что ещё?"
    
    async def _handle_awaiting_date(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Handle when awaiting date information"""
        # Implementation would handle date collection
        session.update_state(DialogState.AWAITING_COMMAND, {})
        await self.session_repo.update(session)
        return "Дата установлена. Что ещё?"
    
    async def _handle_awaiting_location(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Handle when awaiting location information"""
        # Implementation would handle location collection
        session.update_state(DialogState.AWAITING_COMMAND, {})
        await self.session_repo.update(session)
        return "Место установлено. Что ещё?"
    
    async def _handle_confirming(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Handle confirmation state"""
        if intent_dto.name == "CONFIRM_YES":
            session.update_state(DialogState.AWAITING_COMMAND, {})
            await self.session_repo.update(session)
            return "Подтверждено. Что ещё?"
        elif intent_dto.name == "CONFIRM_NO":
            session.update_state(DialogState.AWAITING_COMMAND, {})
            await self.session_repo.update(session)
            return "Отменено. Что ещё?"
        else:
            return "Пожалуйста, скажите да или нет."
    
    async def _handle_error_recovery(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Handle error recovery state"""
        session.update_state(DialogState.AWAITING_COMMAND, {})
        await self.session_repo.update(session)
        return "Давайте начнём сначала. Что вы хотите сделать?"
    
    async def _handle_default(self, session: Session, intent_dto: IntentDTO, text: str) -> str:
        """Default handler for unknown states"""
        session.update_state(DialogState.AWAITING_COMMAND, {})
        await self.session_repo.update(session)
        return "Что вы хотите сделать?"
    
    async def _execute_add_shopping_item(self, command: AddShoppingItemCommand) -> CommandResult:
        """Execute add shopping item command (simulated)"""
        # In a real implementation, this would use the command bus
        # For now, we'll just return a success result
        return CommandResult.success(f"Добавлено {command.item_name} в список")