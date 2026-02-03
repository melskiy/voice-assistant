"""
Process Voice Command Use Case.

User goal: Process a voice command from audio input to text response.
Success guarantee: Returns appropriate response based on intent and state.
Side effects: Updates session state, may trigger command execution.
"""
from uuid import UUID

from ...domain.entities.session import Session
from ...domain.entities.dialog_engine import DialogEngine
from ...domain.entities.intent import Intent
from ...domain.value_objects.audio_chunk import AudioChunk
from ...domain.value_objects.dialog_response import DialogResponse
from ...domain.repositories.session_repository import ISessionRepository
from ..ports.asr_port import ASRPort
from ..ports.nlu_port import NLUPort
from ..ports.tts_port import TTSPort


class ProcessVoiceCommand:
    """
    Use case for processing voice commands.
    
    Orchestrates:
    1. Audio transcription (ASR)
    2. Intent classification (NLU)
    3. Dialog state management
    4. Response generation
    """
    
    def __init__(
        self,
        asr_port: ASRPort,
        nlu_port: NLUPort,
        tts_port: TTSPort | None,
        session_repo: ISessionRepository
    ):
        self.asr_port = asr_port
        self.nlu_port = nlu_port
        self.tts_port = tts_port
        self.session_repo = session_repo
    
    async def execute(
        self, 
        session_id: UUID, 
        audio_chunk: AudioChunk
    ) -> DialogResponse:
        """
        Execute the use case.
        
        Args:
            session_id: Session identifier
            audio_chunk: Audio data to process
            
        Returns:
            Dialog response with text and state
        """
        try:
            # Step 1: Get or create session
            session = await self._get_or_create_session(session_id)
            
            # Step 2: Transcribe audio
            transcription = await self.asr_port.transcribe(audio_chunk)
            
            if not transcription or not transcription.is_final:
                # Return empty response for partial transcriptions
                return DialogResponse(
                    text="",
                    state=session.state,
                    confidence=0.0,
                    session_id=session_id
                )
            
            # Step 3: Classify intent
            intent_dto = await self.nlu_port.classify_intent(transcription.text)
            
            if not intent_dto:
                return DialogResponse.error_response(
                    message="Извините, не удалось распознать команду. Повторите, пожалуйста.",
                    session_id=session_id
                )
            
            # Convert DTO to domain entity
            intent = Intent.create(
                name=intent_dto.name,
                confidence_score=intent_dto.confidence,
                entities=intent_dto.entities
            )
            
            # Step 4: Process with dialog engine
            dialog_engine = DialogEngine(session)
            next_state, response_text = dialog_engine.handle_intent(
                intent, 
                transcription.text
            )
            
            # Step 5: Save updated session
            await self.session_repo.update(session)
            
            # Step 6: Handle special responses
            if response_text == "LIST_REQUEST":
                response_text = await self._get_shopping_list_response(session)
            
            return DialogResponse(
                text=response_text,
                state=next_state,
                confidence=intent.confidence.score,
                intent_name=intent.name,
                session_id=session_id
            )
            
        except Exception as e:
            return DialogResponse.error_response(
                message="Извините, произошла ошибка. Повторите, пожалуйста.",
                session_id=session_id
            )
    
    async def _get_or_create_session(self, session_id: UUID) -> Session:
        """Get existing session or create new one."""
        session = await self.session_repo.get_by_id(session_id)
        
        if not session:
            from ...domain.value_objects.phone_number import PhoneNumber
            session = Session.create(PhoneNumber(number="+unknown"))
            await self.session_repo.save(session)
        
        return session
    
    async def _get_shopping_list_response(self, session: Session) -> str:
        """Generate shopping list response."""
        # This would typically use a query bus
        # For now, return placeholder
        return "Ваш список покупок пуст."
