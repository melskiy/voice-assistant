"""
Mock ASR plugin for testing and fallback scenarios
"""
import asyncio
import random
from typing import Dict, Any
from datetime import datetime

from voice_assistant.infrastructure.plugins.plugin_interface import BasePlugin, ASRPlugin
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.domain.value_objects.audio_chunk import AudioChunk


class MockASRPlugin(BasePlugin, ASRPlugin):
    """Mock ASR plugin for testing purposes"""
    
    def __init__(self):
        super().__init__()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.partial_counter = 0
        
        # Mock Russian phrases for testing
        self.mock_phrases = [
            "добавить молоко в список покупок",
            "создать напоминание на завтра",
            "показать мой список дел",
            "удалить хлеб из списка",
            "напомнить мне позвонить врачу",
            "что у меня в списке покупок",
            "отметить задачу как выполненную"
        ]
    
    @classmethod
    def get_id(cls) -> str:
        return "asr.mock"
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "confidence_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "default": [0.7, 0.95],
                    "description": "Range for random confidence scores"
                },
                "partial_probability": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Probability of generating partial results"
                }
            }
        }
    
    def is_available(self) -> bool:
        """Mock plugin is always available"""
        return True
    
    async def transcribe(self, audio_chunk: AudioChunk) -> TranscriptionDTO:
        """Mock transcription with simulated processing"""
        # Simulate processing delay
        await asyncio.sleep(0.01)
        
        # Determine if this should be a partial or final result
        is_final = audio_chunk.is_final or random.random() > 0.3
        
        if is_final:
            # Generate final result with random phrase
            text = random.choice(self.mock_phrases)
            # Generate confidence with some low values for testing fallback
            if random.random() < 0.2:  # 20% chance of low confidence
                confidence = random.uniform(0.1, 0.6)  # Low confidence range
            else:
                confidence = random.uniform(0.7, 0.95)  # Normal confidence range
        else:
            # Generate partial result (incomplete phrase)
            full_phrase = random.choice(self.mock_phrases)
            words = full_phrase.split()
            partial_length = random.randint(1, max(1, len(words) - 1))
            text = " ".join(words[:partial_length])
            confidence = 0.0  # Partial results don't have confidence
        
        return TranscriptionDTO(
            text=text,
            is_final=is_final,
            confidence=confidence,
            timestamp=audio_chunk.timestamp,
            audio_duration=audio_chunk.duration
        )
    
    async def start_recognition_session(self, session_id: str) -> None:
        """Start a new recognition session"""
        self.active_sessions[session_id] = {
            'start_time': datetime.utcnow(),
            'chunk_count': 0
        }
    
    async def end_recognition_session(self, session_id: str) -> None:
        """End recognition session and cleanup"""
        self.active_sessions.pop(session_id, None)
    
    async def shutdown(self) -> None:
        """Clean up resources"""
        self.active_sessions.clear()