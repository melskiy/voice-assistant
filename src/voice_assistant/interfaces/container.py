import os


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
