"""
Plugin configuration for the voice assistant core.
This file defines which plugins are enabled and their default configurations.
"""

from typing import Dict, Any
import os
from pathlib import Path

# Calculate project root directory (where this file is located: src/plugins/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Default plugin configurations
PLUGIN_CONFIGS: Dict[str, Dict[str, Any]] = {
    # ASR Plugins
    "asr.vosk": {
        "enabled": True,
        "model_path": os.getenv("VOSK_MODEL_PATH", str(_PROJECT_ROOT / "models" / "vosk-model-small-ru-0.22")),
        "sample_rate": int(os.getenv("VOSK_SAMPLE_RATE", "8000")),
        "partial_results": os.getenv("VOSK_PARTIAL_RESULTS", "true").lower() == "true"
    },
    
    # "asr.whisper_cpp": {
    #     "enabled": os.getenv("WHISPER_CPP_ENABLED", "false").lower() == "true",
    #     "whisper_cpp_path": os.getenv("WHISPER_CPP_PATH", "./bin/whisper"),
    #     "model_path": os.getenv("WHISPER_MODEL_PATH", "./models/ggml-small.bin"),
    #     "beam_size": int(os.getenv("WHISPER_BEAM_SIZE", "5")),
    #     "threads": int(os.getenv("WHISPER_THREADS", "4")),
    #     "language": os.getenv("WHISPER_LANGUAGE", "ru")
    # },
    
    # NLU Plugins
    "nlu.regex": {
        "enabled": os.getenv("NLU_REGEX_ENABLED", "true").lower() == "true",
        "language": os.getenv("NLU_LANGUAGE", "ru"),
        "case_sensitive": os.getenv("NLU_CASE_SENSITIVE", "false").lower() == "true"
    },
    
    "nlu.sklearn": {
        "enabled": os.getenv("NLU_SKLEARN_ENABLED", "true").lower() == "true",
        "language": os.getenv("NLU_LANGUAGE", "ru"),
        "train_on_init": os.getenv("NLU_SKLEARN_TRAIN_ON_INIT", "true").lower() == "true",
        "model_path": os.getenv("NLU_SKLEARN_MODEL_PATH", "")
    },
    
    # TTS Plugins
    "tts.mock": {
        "enabled": os.getenv("TTS_MOCK_ENABLED", "true").lower() == "true",
        "delay_ms": int(os.getenv("TTS_MOCK_DELAY_MS", "0"))
    },
    
    "tts.silero": {
        "enabled": os.getenv("TTS_SILERO_ENABLED", "true").lower() == "true",
        "model_id": os.getenv("TTS_SILERO_MODEL_ID", "v3_ru.pt"),
        "sample_rate": int(os.getenv("TTS_SILERO_SAMPLE_RATE", "48000")),
        "speaker": os.getenv("TTS_SILERO_SPEAKER", "baya"),
        "device": os.getenv("TTS_SILERO_DEVICE", "cpu")
    },
    
    # Storage Plugins
    "storage.postgres": {
        "enabled": os.getenv("STORAGE_POSTGRES_ENABLED", "true").lower() == "true",
        "connection_string": os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/voice_assistant"),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "voice_assistant"),
        "username": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "password"),
        "pool_min_size": int(os.getenv("POSTGRES_POOL_MIN_SIZE", "5")),
        "pool_max_size": int(os.getenv("POSTGRES_POOL_MAX_SIZE", "20"))
    },
    
    "storage.redis": {
        "enabled": os.getenv("STORAGE_REDIS_ENABLED", "true").lower() == "true",
        "url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": int(os.getenv("REDIS_DB", "0")),
        "password": os.getenv("REDIS_PASSWORD", ""),
        "default_ttl": int(os.getenv("REDIS_DEFAULT_TTL", "1800")),
        "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    },

    # Messaging Plugins
    "messaging.rabbitmq": {
        "enabled": os.getenv("MESSAGING_RABBITMQ_ENABLED", "true").lower() == "true",
        "url": os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        "host": os.getenv("RABBITMQ_HOST", "localhost"),
        "port": int(os.getenv("RABBITMQ_PORT", "5672")),
        "username": os.getenv("RABBITMQ_USER", "guest"),
        "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
        "virtual_host": os.getenv("RABBITMQ_VHOST", "/"),
        "exchange_name": os.getenv("RABBITMQ_EXCHANGE", "voice_assistant_exchange"),
        "exchange_type": os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")
    }
}

# Default plugin selections (can be overridden by environment variables)
DEFAULT_PLUGINS = {
    "asr": os.getenv("DEFAULT_ASR_PLUGIN", "asr.vosk"),
    "nlu": os.getenv("DEFAULT_NLU_PLUGIN", "nlu.regex"),
    "tts": os.getenv("DEFAULT_TTS_PLUGIN", "tts.silero")
}


def get_enabled_plugin_configs() -> Dict[str, Dict[str, Any]]:
    """Get only enabled plugin configurations"""
    return {
        plugin_id: config 
        for plugin_id, config in PLUGIN_CONFIGS.items() 
        if config.get("enabled", False)
    }


def get_plugin_config(plugin_id: str) -> Dict[str, Any]:
    """Get configuration for a specific plugin"""
    return PLUGIN_CONFIGS.get(plugin_id, {})


def is_plugin_enabled(plugin_id: str) -> bool:
    """Check if a plugin is enabled"""
    return PLUGIN_CONFIGS.get(plugin_id, {}).get("enabled", False)


def get_default_plugin(plugin_type: str) -> str:
    """Get the default plugin for a given type"""
    return DEFAULT_PLUGINS.get(plugin_type, "")