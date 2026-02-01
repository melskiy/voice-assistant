from typing import Any, Protocol, runtime_checkable
from enum import Enum
from rodi import Container


class PluginType(Enum):
    ASR = "asr"
    NLU = "nlu"
    TTS = "tts"
    STORAGE = "storage"


class Plugin(Protocol):
    """Base interface for all plugins using Protocol for better type checking"""
    
    @classmethod
    def get_id(cls) -> str:
        """Get unique plugin identifier (e.g., 'asr.vosk', 'tts.silero')"""
        ...
    
    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Get JSON schema for plugin configuration"""
        ...
    
    @classmethod
    def register_dependencies(cls, container: Container, config: dict[str, Any]) -> None:
        """Register plugin dependencies in IoC container"""
        ...
    
    def is_available(self) -> bool:
        """Check if plugin can run in current environment"""
        ...


class BasePlugin:
    """Base implementation for plugins with common functionality"""
    
    @classmethod
    def get_id(cls) -> str:
        """Get unique plugin identifier (e.g., 'asr.vosk', 'tts.silero')"""
        raise NotImplementedError
    
    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Get JSON schema for plugin configuration"""
        raise NotImplementedError
    
    @classmethod
    def register_dependencies(cls, container: Container, config: dict[str, Any]) -> None:
        """Register plugin dependencies in IoC container"""
        # Default implementation - register the plugin class as singleton
        container.add_singleton(cls, lambda: cls._create_instance(config))
    
    @classmethod
    def _create_instance(cls, config: dict[str, Any]):
        """Create and initialize plugin instance"""
        instance = cls()
        # Store config for later use if needed
        instance._config = config
        return instance
    
    def is_available(self) -> bool:
        """Check if plugin can run in current environment"""
        raise NotImplementedError

@runtime_checkable
class ASRPlugin(Protocol):
    """Interface for ASR (Automatic Speech Recognition) plugins"""
    
    async def transcribe(self, audio_chunk) -> 'TranscriptionDTO':
        """Transcribe audio chunk to text"""
        ...
    
    async def start_recognition_session(self, session_id: str) -> None:
        """Start a new recognition session"""
        ...
    
    async def end_recognition_session(self, session_id: str) -> None:
        """End recognition session and cleanup"""
        ...

@runtime_checkable
class NLUPlugin(Protocol):
    """Interface for NLU (Natural Language Understanding) plugins"""
    
    async def classify_intent(self, text: str) -> 'IntentDTO':
        """Classify intent from text"""
        ...
    
    async def extract_entities(self, text: str) -> dict[str, Any]:
        """Extract entities from text"""
        ...
    
    async def process_text(self, text: str) -> 'IntentDTO':
        """Process text to extract intent and entities"""
        ...

@runtime_checkable
class TTSPlugin(Protocol):
    """Interface for TTS (Text-to-Speech) plugins"""
    
    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech from text, returns audio bytes"""
        ...
    
    async def synthesize_to_file(self, text: str, output_path: str) -> None:
        """Synthesize speech to audio file"""
        ...