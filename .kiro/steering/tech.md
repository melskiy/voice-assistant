# Technology Stack

## Core Technologies

- **Runtime**: Python 3.12+
- **Web Framework**: FastAPI for HTTP APIs
- **Communication**: gRPC for internal services, HTTP/REST for external APIs
- **Dependency Injection**: rodi
- **Database**: PostgreSQL with asyncpg
- **Cache**: Redis with redis.asyncio
- **Message Queue**: RabbitMQ for event-driven communication
- **Containerization**: Docker with multi-stage builds

## Audio Processing Stack

- **ASR Engines**: Vosk (lightweight), Whisper.cpp (accurate)
- **Audio Libraries**: sounddevice, librosa
- **NLU**: spaCy, scikit-learn
- **TTS**: Silero, Piper

## Development Tools

- **Testing**: pytest, pytest-cov
- **Code Quality**: black (formatting), flake8 (linting), mypy (type checking)
- **Build System**: setuptools with pyproject.toml

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run main application
python -m src.main

# Run tests
pytest
pytest --cov

# Code formatting and linting
black src/
flake8 src/
mypy src/
```

### Docker Operations
```bash
# Build images
make build
# or manually:
docker build -f image.Dockerfile -t voice-assistant-base:latest .
docker build -t voice-assistant-app:latest .

# Start all services
make all

# Start infrastructure only (PostgreSQL, Redis, RabbitMQ)
make infra

# Start application services only
make services

# View logs
make logs

# Stop all services
make stop

# Clean up (including volumes)
make clean

# Check service status
make status
```

### Service Management
```bash
# Shell into specific service
make shell-gateway-service
make shell-asr-service

# Rebuild and restart
make rebuild
```

## Configuration

- **Plugin Configuration**: `src/plugins/config.py`
- **Environment Variables**: `.env` file
- **Docker Compose**: Separate files for infrastructure and services
- **Service Requirements**: Individual `requirements.txt` per service