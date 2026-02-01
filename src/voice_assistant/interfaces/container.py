from rodi import Container
from grpc import Channel, insecure_channel
from typing import Any, Dict, Optional
import os
from voice_assistant.domain.repositories.session_repository import ISessionRepository
from voice_assistant.domain.repositories.shopping_repository import IShoppingRepository
from voice_assistant.domain.repositories.reminder_repository import IReminderRepository
from voice_assistant.domain.entities.call_session import CallSession
from voice_assistant.infrastructure.plugins.plugin_manager import IoC_PluginManager
from voice_assistant.application.services.voice_dialog_orchestrator import VoiceDialogOrchestrator


class Config:
    """Configuration class for the voice assistant core"""
    
    def __init__(self):
        # Database settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./voice_assistant.db")
        self.database_pool_size = int(os.getenv("DATABASE_POOL_SIZE", "5"))
        
        # Redis settings
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # RabbitMQ settings
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        
        # gRPC service URLs
        self.asr_service_url = os.getenv("ASR_SERVICE_URL", "localhost:50051")
        self.nlu_service_url = os.getenv("NLU_SERVICE_URL", "localhost:50052")
        self.dialog_service_url = os.getenv("DIALOG_SERVICE_URL", "localhost:50053")
        self.tts_service_url = os.getenv("TTS_SERVICE_URL", "localhost:50054")
        
        # Plugin settings
        self.plugins_directory = os.getenv("PLUGINS_DIR", "src/plugins")
        
        # FreeSWITCH settings
        self.freeswitch_host = os.getenv("FREESWITCH_HOST", "localhost")
        self.freeswitch_port = int(os.getenv("FREESWITCH_PORT", "8021"))
        self.freeswitch_password = os.getenv("FREESWITCH_PASSWORD", "ClueCon")
        
        # Application settings
        self.session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        self.max_retry_attempts = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
        
        # Audio processing settings
        self.audio_chunk_duration_ms = int(os.getenv("AUDIO_CHUNK_DURATION_MS", "200"))
        self.audio_sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE", "8000"))
        self.audio_channels = int(os.getenv("AUDIO_CHANNELS", "1"))
        
        # Performance settings
        self.max_concurrent_sessions = int(os.getenv("MAX_CONCURRENT_SESSIONS", "100"))
        self.grpc_max_message_length = int(os.getenv("GRPC_MAX_MESSAGE_LENGTH", "4194304"))  # 4MB


def create_container(plugin_configs: Dict[str, Dict[str, Any]] = None) -> Container:
    """Create and configure the DI container using RoDI with plugin support"""
    container = Container()
    
    # Register configuration
    container.add_singleton(Config)
    
    # Register CallSession factory
    def call_session_factory(caller_id: str, metadata: Optional[Dict[str, Any]] = None) -> CallSession:
        return CallSession.create(caller_id, metadata)
    
    # Register the factory function using the correct rodi API
    container.add_instance(call_session_factory, "call_session_factory")
    
    # Register gRPC channels
    config = Config()
    
    container.add_instance(insecure_channel(config.asr_service_url), "asr_channel")
    container.add_instance(insecure_channel(config.nlu_service_url), "nlu_channel") 
    container.add_instance(insecure_channel(config.dialog_service_url), "dialog_channel")
    container.add_instance(insecure_channel(config.tts_service_url), "tts_channel")
    
    # Register plugin manager and discover plugins (simplified for now)
    try:
        plugin_manager = IoC_PluginManager(container)
        container.add_instance(plugin_manager, "plugin_manager")
        
        # Load and register plugins
        if plugin_configs:
            registered_plugins = plugin_manager.discover_and_register_plugins(plugin_configs)
            print(f"Registered plugins: {registered_plugins}")
        else:
            # Use default configuration from plugins/config.py
            try:
                from plugins.config import get_enabled_plugin_configs
                default_configs = get_enabled_plugin_configs()
                registered_plugins = plugin_manager.discover_and_register_plugins(default_configs)
                print(f"Registered plugins with default config: {registered_plugins}")
            except ImportError:
                print("Plugin configuration not available, skipping plugin registration")
    except Exception as e:
        print(f"Plugin manager initialization failed: {e}")
    
    # Register services (simplified for now)
    # container.add_transient(VoiceDialogOrchestrator)
    
    return container


def get_container(plugin_configs: Dict[str, Dict[str, Any]] = None) -> Container:
    """Get the configured container with plugins"""
    return create_container(plugin_configs)


def resolve_dependency(dependency_type: type, plugin_configs: Dict[str, Dict[str, Any]] = None) -> Any:
    """Helper to resolve dependencies from container"""
    container = get_container(plugin_configs)
    return container.resolve(dependency_type)


def create_service_container(service_name: str) -> Container:
    """Create a container configured for a specific service"""
    container = create_container()
    
    # Add service-specific configurations
    if service_name == "asr_service":
        # ASR service might need specific ASR plugins
        from plugins.config import get_default_plugin, get_plugin_config
        default_asr = get_default_plugin("asr")
        if default_asr:
            print(f"ASR service using plugin: {default_asr}")
    
    elif service_name == "nlu_service":
        # NLU service might need specific NLU plugins
        from plugins.config import get_default_plugin
        default_nlu = get_default_plugin("nlu")
        if default_nlu:
            print(f"NLU service using plugin: {default_nlu}")
    
    elif service_name == "tts_service":
        # TTS service might need specific TTS plugins
        from plugins.config import get_default_plugin
        default_tts = get_default_plugin("tts")
        if default_tts:
            print(f"TTS service using plugin: {default_tts}")
    
    return container