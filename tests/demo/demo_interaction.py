"""
Demo interaction for voice assistant.

Demonstrates how to use the voice assistant components.
This is for testing and development purposes.
"""
import asyncio
from uuid import uuid4
from datetime import datetime

from voice_assistant.domain.value_objects.audio_chunk import AudioChunk
from voice_assistant.application.use_cases.process_voice_command import ProcessVoiceCommand
from voice_assistant.application.ports.asr_port import ASRPort
from voice_assistant.application.ports.nlu_port import NLUPort
from voice_assistant.application.ports.tts_port import TTSPort
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.application.dto.intent_dto import IntentDTO


class MockASRPlugin(ASRPort):
    """Mock ASR plugin for demo."""
    
    async def transcribe(self, audio_chunk: AudioChunk) -> TranscriptionDTO:
        # Simulate transcription
        return TranscriptionDTO(
            text="добавь молоко в список покупок",
            is_final=True,
            confidence=0.95,
            timestamp=datetime.utcnow(),
            audio_duration=audio_chunk.duration
        )
    
    async def start_recognition_session(self, session_id) -> None:
        pass
    
    async def end_recognition_session(self, session_id) -> None:
        pass
    
    def is_available(self) -> bool:
        return True


class MockNLUPlugin(NLUPort):
    """Mock NLU plugin for demo."""
    
    async def classify_intent(self, text: str) -> IntentDTO:
        # Simple rule-based classification for demo
        if "добавь" in text.lower() or "список" in text.lower():
            return IntentDTO(
                name="ADD_SHOPPING_ITEM",
                confidence=0.9,
                entities={"item": "молоко"}
            )
        elif "напоминание" in text.lower():
            return IntentDTO(
                name="CREATE_REMINDER",
                confidence=0.85,
                entities={"description": "напоминание"}
            )
        else:
            return IntentDTO(
                name="UNKNOWN",
                confidence=0.5,
                entities={}
            )
    
    async def extract_entities(self, text: str) -> dict:
        return {}
    
    async def process_text(self, text: str) -> IntentDTO:
        return await self.classify_intent(text)
    
    def is_available(self) -> bool:
        return True


class MockTTSPlugin(TTSPort):
    """Mock TTS plugin for demo."""
    
    async def synthesize(self, text: str) -> bytes:
        return b"mock_audio_data"
    
    async def synthesize_streaming(self, text: str):
        yield AudioChunk.create(b"mock_chunk", is_final=True)
    
    async def synthesize_to_file(self, text: str, output_path: str) -> None:
        pass
    
    def is_available(self) -> bool:
        return True


async def run_demo_interaction():
    """Run a demo interaction with the voice assistant."""
    print("\n" + "=" * 50)
    print("Voice Assistant Demo Interaction")
    print("=" * 50 + "\n")
    
    # Create mock plugins
    asr_plugin = MockASRPlugin()
    nlu_plugin = MockNLUPlugin()
    tts_plugin = MockTTSPlugin()
    
    # Create mock repositories
    from tests.mocks.mock_repositories import (
        MockSessionRepository,
        MockShoppingRepository,
        MockReminderRepository
    )
    
    session_repo = MockSessionRepository()
    shopping_repo = MockShoppingRepository()
    reminder_repo = MockReminderRepository()
    
    # Create use case
    use_case = ProcessVoiceCommand(
        asr_port=asr_plugin,
        nlu_port=nlu_plugin,
        tts_port=tts_plugin,
        session_repo=session_repo
    )
    
    # Create demo audio chunk
    session_id = uuid4()
    audio_chunk = AudioChunk.create(
        data=b"dummy_audio_data",
        sample_rate=8000,
        channels=1,
        sequence_number=1,
        duration=1.0,
        is_final=True
    )
    
    print(f"Session ID: {session_id}")
    print(f"Audio chunk: {len(audio_chunk.data)} bytes, {audio_chunk.duration:.2f}s")
    print("\nProcessing...\n")
    
    # Process voice command
    response = await use_case.execute(session_id, audio_chunk)
    
    print(f"Response text: {response.text}")
    print(f"Dialog state: {response.state.value}")
    print(f"Confidence: {response.confidence:.2f}")
    if response.intent_name:
        print(f"Intent: {response.intent_name}")
    
    print("\n" + "=" * 50)
    print("Demo completed successfully!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo_interaction())
