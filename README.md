# Voice Assistant Core

A modular voice assistant system with pluggable ASR, NLU, and TTS engines, designed for integration with FreeSWITCH.

## Architecture

The system follows Domain-Driven Design (DDD) principles with three main layers:

- **Domain Layer**: Contains core business logic and entities with no external dependencies
- **Application Layer**: Implements use cases and orchestrates domain objects
- **Infrastructure Layer**: Handles external dependencies like databases, message queues, and plugins

## Features

- **Pluggable Architecture**: Swap ASR, NLU, and TTS engines without code changes
- **Offline Operation**: All processing works without internet connectivity
- **Russian Language Support**: Optimized for Russian language voice processing
- **Microservices Ready**: Designed for containerized deployment
- **FreeSWITCH Integration**: Ready for telephony integration

## Plugin System

The voice assistant uses a flexible plugin system that supports:

### ASR Plugins
- **Vosk ASR**: Lightweight, fast recognition for Russian
- **Whisper.cpp**: More accurate but resource-intensive

### NLU Plugins  
- **Regex-based**: Pattern matching for intent recognition
- **Scikit-learn**: ML-based intent classification

### TTS Plugins
- **Silero TTS**: High-quality Russian text-to-speech
- **Mock TTS**: For testing purposes

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd voice-assistant-core
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download required models (for Vosk ASR):
```bash
# Download Russian Vosk model
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
mv vosk-model-small-ru-0.22 models/
```

## Configuration

Configure plugins in `src/plugins/config.py`:

```python
PLUGIN_CONFIGS = {
    "asr.vosk": {
        "enabled": True,
        "model_path": "./models/vosk-model-small-ru-0.22",
        "sample_rate": 8000,
        "partial_results": True
    },
    # ... other configurations
}
```
## Running the System

### Development Mode
```bash
python -m src.main
```

### Docker Deployment

The system uses a modular Docker setup with a single voice_assistant image and separated infrastructure and services:

#### Build Images First
```bash
# Build the base image first
docker build -f image.Dockerfile -t voice-assistant-base:latest .

# Build the application image (uses the base image)
docker build -t voice-assistant-app:latest .

# Or build both with docker-compose
docker-compose build
```

#### Quick Start - All Services
```bash
# Make sure to build images first, then run
make all
# or
docker-compose up -d
```

#### Separate Infrastructure and Services
```bash


# Start application services (Gateway, ASR, NLU, etc.)
make services
# or
docker-compose -f docker-compose.yml up -d
```

#### Useful Commands
```bash
make help           # Show all available commands
make status         # Show running containers
make logs           # View logs from all services
make stop           # Stop all services
make clean          # Stop and remove volumes
make rebuild        # Rebuild and restart all services
```

## Project Structure

```
├── src/
│   ├── voice_assistant/
│   │   ├── domain/          # Domain layer (business logic)
│   │   ├── application/     # Application layer (use cases)
│   │   └── infrastructure/  # Infrastructure layer (plugins, persistence)
│   ├── services/            # Microservices
│   └── plugins/             # Plugin implementations
├── docs/                    # Documentation
├── plans/                   # Architecture plans
├── image.Dockerfile         # Base image with common dependencies
├── Dockerfile               # Application image (extends base image)
├── docker-compose.yml       # Main compose file (all services)
├── docker-compose.infra.yml # Infrastructure services only
├── docker-compose.services.yml # Application services only
├── Makefile                 # Convenient commands
├── requirements.txt         # Core requirements (voice_assistant by all services)
├── requirements-dev.txt     # Development requirements
└── tests/                   # Test suite
```

## Docker Image Optimization

The system uses a voice_assistant image approach to reduce redundancy:

- **image.Dockerfile**: Base image with common Python dependencies and system libraries
- **Dockerfile**: Application image that extends the base image with application code
- **All services**: Use the same application image with different commands
- **voice_assistant requirements**: Single requirements.txt file for all services

## Infrastructure Separation

Infrastructure services (PostgreSQL, Redis, RabbitMQ) are separated from application services:
- Can be managed independently
- Allows for independent scaling
- Infrastructure can run continuously while services are updated
- Better resource allocation

## Contributing


1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.