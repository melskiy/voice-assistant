.PHONY: help infra services all stop clean logs build-protos test

# Help target
help:
	@echo "Voice Assistant Makefile"
	@echo "========================"
	@echo "Available commands:"
	@echo "  make help         - Show this help message"
	@echo "  make infra        - Start infrastructure services (PostgreSQL, Redis, RabbitMQ)"
	@echo "  make services     - Start application services (Gateway, ASR, NLU, etc.)"
	@echo "  make all          - Start all services (infrastructure + application)"
	@echo "  make stop         - Stop all running services"
	@echo "  make clean        - Stop all services and remove volumes"
	@echo "  make logs         - View logs from all services"
	@echo "  make build        - Build Docker images (base and app)"
	@echo "  make build-protos - Compile Protocol Buffer definitions"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-property - Run property-based tests only"

# Start infrastructure services only
infra:
	docker-compose -f docker-compose.infra.yml up -d

# Start application services only
services:
	docker-compose -f docker-compose.services.yml up -d

# Start all services
all:
	docker-compose up -d

# Stop all services
stop:
	docker-compose down
	docker-compose -f docker-compose.infra.yml down
	docker-compose -f docker-compose.services.yml down

# Clean up everything including volumes
clean:
	docker-compose down -v
	docker-compose -f docker-compose.infra.yml down -v
	docker-compose -f docker-compose.services.yml down -v

# View logs
logs:
	docker-compose logs -f

# Build Docker images
build:
	docker build -f image.Dockerfile -t voice-assistant-base:latest .
	docker build -t voice-assistant-app:latest .

# Rebuild and start services
rebuild:
	docker-compose down
	docker build -f image.Dockerfile -t voice-assistant-base:latest .
	docker build -t voice-assistant-app:latest .
	docker-compose up -d

# Show status of running containers
status:
	docker-compose ps
	docker-compose -f docker-compose.infra.yml ps
	docker-compose -f docker-compose.services.yml ps

# Shell into a specific service
shell-%:
	docker-compose exec $* /bin/sh

# Example: make shell-gateway-service

# Compile Protocol Buffer definitions
build-protos:
	python scripts/compile_protos.py

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest -m "not property"

# Run property-based tests only
test-property:
	pytest -m property

# Install development dependencies
install-dev:
	pip install -e ".[dev]"

# Format code
format:
	black src/ tests/

# Lint code
lint:
	flake8 src/ tests/
	mypy src/

# Type check
typecheck:
	mypy src/