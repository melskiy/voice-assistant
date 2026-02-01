# Project Structure

## Architecture Pattern

The project follows **Domain-Driven Design (DDD)** with clean architecture principles:

- **Domain Layer**: Core business logic with no external dependencies
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: External dependencies (databases, plugins, APIs)

## Directory Structure

```
├── src/
│   ├── voice_assistant/                    # voice_assistant components across services
│   │   ├── domain/               # Domain layer (business logic)
│   │   │   ├── entities/         # Domain entities
│   │   │   ├── repositories/     # Repository interfaces
│   │   │   └── value_objects/    # Value objects
│   │   ├── application/          # Application layer (use cases)
│   │   │   ├── commands/         # Command objects
│   │   │   ├── dto/              # Data transfer objects
│   │   │   ├── handlers/         # Command/query handlers
│   │   │   └── services/         # Application services
│   │   └── infrastructure/       # Infrastructure layer
│   │       ├── plugins/          # Plugin system
│   │       ├── persistence/      # Database implementations
│   │       ├── messaging/        # Message queue implementations
│   │       └── external/         # External service integrations
│   ├── services/                 # Microservices
│   │   ├── asr_service/          # Speech recognition service
│   │   ├── nlu_service/          # Natural language understanding
│   │   ├── dialog_service/       # Dialog management
│   │   ├── gateway_service/      # API gateway
│   │   └── notification_service/ # Notification handling
│   └── plugins/                  # Plugin implementations
│       ├── asr-vosk/            # Vosk ASR plugin
│       ├── asr-whisper-cpp/     # Whisper.cpp ASR plugin
│       ├── nlu-regex/           # Regex NLU plugin
│       ├── nlu-sklearn/         # ML NLU plugin
│       ├── tts-silero/          # Silero TTS plugin
│       └── storage-*/           # Storage plugins
├── docs/                        # Documentation
├── plans/                       # Architecture plans and decisions
├── infrastructure/              # Infrastructure configuration
└── models/                      # ML models directory
```

## Plugin System Architecture

### Plugin Interface
- Base `Plugin` class in `src/voice_assistant/infrastructure/plugins/plugin_interface.py`
- Specialized interfaces: `ASRPlugin`, `NLUPlugin`, `TTSPlugin`
- Plugin registry and manager for dynamic loading

### Plugin Structure
```
src/plugins/{plugin-name}/
├── plugin.py              # Plugin implementation
└── requirements.txt       # Plugin-specific dependencies
```

### Plugin Configuration
- Central configuration in `src/plugins/config.py`
- Environment-based overrides
- Runtime plugin selection

## Service Communication

### Internal Communication
- **gRPC**: High-performance binary protocol for service-to-service
- **Protocol Buffers**: Schema definition and serialization
- **Streaming**: Bidirectional streaming for audio processing

### External Communication
- **HTTP/REST**: Gateway service for FreeSWITCH integration
- **JSON**: Standard API format for external clients

### Event Communication
- **RabbitMQ**: Asynchronous event-driven messaging
- **Topic Exchange**: Flexible routing for notifications and logging

## Naming Conventions

### Services
- Format: `{purpose}-service` (e.g., `asr-service`, `nlu-service`)
- Module path: `src.services.{service_name}.main`

### Plugins
- Format: `{type}-{implementation}` (e.g., `asr-vosk`, `tts-silero`)
- Plugin ID: `{type}.{implementation}` (e.g., `asr.vosk`, `tts.silero`)

### Domain Objects
- **Entities**: Business objects with identity
- **Value Objects**: Immutable objects without identity
- **DTOs**: Data transfer between layers
- **Commands**: Action requests with validation

## File Organization Rules

1. **voice_assistant Code**: Place in `src/voice_assistant/` if used by multiple services
2. **Service-Specific**: Keep in respective service directory
3. **Plugin Isolation**: Each plugin in separate directory with own dependencies
4. **Configuration**: Centralized in `config.py` files per layer
5. **Tests**: Co-located with source files using `.test.py` suffix