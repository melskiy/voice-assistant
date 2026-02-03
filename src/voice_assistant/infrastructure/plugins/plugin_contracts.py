"""
Plugin contracts and interfaces for the voice assistant.

This module defines the core interfaces that all plugins must implement.
Following the Dependency Inversion Principle, these interfaces are defined
in the infrastructure layer and implemented by specific plugins.
"""

from typing import Any, Dict, Protocol, runtime_checkable, Optional
from abc import ABC, abstractmethod
from rodi import Container


class PluginMetadata:
    """Metadata about a plugin."""
    
    def __init__(
        self,
        plugin_id: str,
        name: str,
        version: str,
        description: str,
        author: str,
        dependencies: list[str] = None
    ):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies or []


class IPluginRegistration(ABC):
    """
    Interface for plugin registration.
    
    This is the ONLY class that interacts with the IoC container.
    It contains NO business logic - only dependency registration.
    
    Example:
        class MyPluginRegistration(IPluginRegistration):
            @classmethod
            def get_metadata(cls) -> PluginMetadata:
                return PluginMetadata(
                    plugin_id="asr.vosk",
                    name="Vosk ASR",
                    version="1.0.0",
                    description="Vosk-based speech recognition",
                    author="Voice Assistant Team"
                )
            
            @classmethod
            def get_config_schema(cls) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "model_path": {"type": "string"},
                        "sample_rate": {"type": "number", "default": 8000}
                    },
                    "required": ["model_path"]
                }
            
            @classmethod
            def register(cls, container: Container, config: Dict[str, Any]) -> None:
                # Register configuration
                container.add_instance(config, name="vosk_config")
                
                # Register factory for model
                container.add_transient(
                    IVoskModel,
                    lambda c: VoskModelFactory.create(c.resolve(dict, name="vosk_config"))
                )
                
                # Register service implementation
                container.add_singleton(IAsrService, VoskAsrService)
    """
    
    @classmethod
    @abstractmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration validation.
        
        Returns:
            Dictionary conforming to JSON Schema format.
        """
        pass
    
    @classmethod
    @abstractmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register plugin dependencies in the IoC container.
        
        This method should ONLY register dependencies, not create instances
        or execute business logic. Use lazy factories where possible.
        
        Args:
            container: The IoC container to register dependencies in
            config: Plugin configuration dictionary
        """
        pass
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if the plugin can be registered in the current environment.
        
        Override this to check for required system dependencies.
        
        Returns:
            True if the plugin can be registered, False otherwise
        """
        return True


# =============================================================================
# Service Interfaces (Contracts)
# =============================================================================

@runtime_checkable
class IAsrService(Protocol):
    """Interface for Automatic Speech Recognition services."""
    
    async def transcribe(self, audio_data: bytes) -> 'TranscriptionResult':
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            TranscriptionResult with text and confidence
        """
        ...
    
    async def start_session(self, session_id: str) -> None:
        """Start a new recognition session."""
        ...
    
    async def end_session(self, session_id: str) -> None:
        """End recognition session and cleanup."""
        ...


@runtime_checkable
class INluService(Protocol):
    """Interface for Natural Language Understanding services."""
    
    async def classify_intent(self, text: str) -> 'IntentResult':
        """
        Classify intent from text.
        
        Args:
            text: Input text to classify
            
        Returns:
            IntentResult with intent name, confidence, and entities
        """
        ...
    
    async def extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extract entities from text for a specific intent.
        
        Args:
            text: Input text
            intent: Classified intent name
            
        Returns:
            Dictionary of extracted entities
        """
        ...


@runtime_checkable
class ITtsService(Protocol):
    """Interface for Text-to-Speech services."""
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio data as bytes
        """
        ...
    
    async def synthesize_to_file(self, text: str, output_path: str) -> None:
        """
        Synthesize speech and save to file.
        
        Args:
            text: Text to synthesize
            output_path: Path to save audio file
        """
        ...


@runtime_checkable
class IStorageService(Protocol):
    """Interface for storage services (databases, caches)."""
    
    async def connect(self) -> None:
        """Establish connection to storage."""
        ...
    
    async def disconnect(self) -> None:
        """Close connection to storage."""
        ...
    
    async def health_check(self) -> bool:
        """Check if storage is accessible."""
        ...


@runtime_checkable
class IMessagingService(Protocol):
    """Interface for messaging services (RabbitMQ, Kafka, etc.)."""
    
    async def connect(self) -> None:
        """Establish connection to messaging broker."""
        ...
    
    async def disconnect(self) -> None:
        """Close connection to messaging broker."""
        ...
    
    async def publish(self, routing_key: str, message: bytes) -> None:
        """Publish a message to the broker."""
        ...
    
    async def subscribe(self, queue: str, handler: callable) -> None:
        """Subscribe to a queue with a message handler."""
        ...


# =============================================================================
# Result Types
# =============================================================================

class TranscriptionResult:
    """Result of ASR transcription."""
    
    def __init__(
        self,
        text: str,
        confidence: float,
        is_final: bool = True,
        language: Optional[str] = None,
        alternatives: list = None
    ):
        self.text = text
        self.confidence = confidence
        self.is_final = is_final
        self.language = language
        self.alternatives = alternatives or []


class IntentResult:
    """Result of NLU intent classification."""
    
    def __init__(
        self,
        intent: str,
        confidence: float,
        entities: Dict[str, Any] = None,
        raw_text: str = ""
    ):
        self.intent = intent
        self.confidence = confidence
        self.entities = entities or {}
        self.raw_text = raw_text


# =============================================================================
# Base Service Implementations
# =============================================================================

class BaseService(ABC):
    """
    Base class for all plugin services.
    
    Services should receive all dependencies through the constructor
    and have no knowledge of the IoC container.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service with runtime resources."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup and release resources."""
        pass


class BaseAsrService(BaseService, IAsrService):
    """Base class for ASR service implementations."""
    pass


class BaseNluService(BaseService, INluService):
    """Base class for NLU service implementations."""
    pass


class BaseTtsService(BaseService, ITtsService):
    """Base class for TTS service implementations."""
    pass


class BaseStorageService(BaseService, IStorageService):
    """Base class for storage service implementations."""
    pass


class BaseMessagingService(BaseService, IMessagingService):
    """Base class for messaging service implementations."""
    pass
