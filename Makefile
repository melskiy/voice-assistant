# Voice Assistant Makefile

# Variables
PYTHON := python3.12
PIP := pip
DOCKER := docker
COMPOSE := docker-compose

# Default target
.PHONY: help
help: ## Show this help
	@echo "Voice Assistant Makefile"
	@echo ""
	@echo "Usage:"
	@grep -E '^[a-zA-Z_0-9%-]+:.*?## .*$$' $(word 1,$(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# Development targets
.PHONY: install
install: ## Install project dependencies
	$(PIP) install -r requirements.txt

.PHONY: install-dev
install-dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install -r src/services/nlu_service/test_requirements.txt

.PHONY: run-gateway
run-gateway: ## Run gateway service
	$(PYTHON) -m src.services.gateway_service.main

.PHONY: run-asr
run-asr: ## Run ASR service
	$(PYTHON) -m src.services.asr_service.main

.PHONY: run-nlu
run-nlu: ## Run NLU service
	$(PYTHON) -m src.services.nlu_service.main

.PHONY: run-tts
run-tts: ## Run TTS service
	$(PYTHON) -m src.services.tts_service.main

.PHONY: run-dialog
run-dialog: ## Run dialog service
	$(PYTHON) -m src.services.dialog_service.main

.PHONY: run-storage
run-storage: ## Run storage service
	$(PYTHON) -m src.services.storage_service.main

.PHONY: run-notification
run-notification: ## Run notification service
	$(PYTHON) -m src.services.notification_service.main

.PHONY: run-all
run-all: ## Run all services (in development mode, requires multiple terminals)
	@echo "Run each service in a separate terminal:"
	@echo "make run-asr"
	@echo "make run-nlu"
	@echo "make run-tts"
	@echo "make run-dialog"
	@echo "make run-storage"
	@echo "make run-notification"
	@echo "make run-gateway"

# Docker targets
.PHONY: docker-build
docker-build: ## Build Docker image
	$(DOCKER) build -t voice_assistant:latest .

.PHONY: docker-run-infra
docker-run-infra: ## Run infrastructure services
	cd infrastructure && $(COMPOSE) up -d

.PHONY: docker-run-app
docker-run-app: ## Run application services
	$(COMPOSE) up -d

.PHONY: docker-run-all
docker-run-all: ## Run all services with Docker
	$(COMPOSE) -f docker-compose.all.yml up -d

.PHONY: docker-down
docker-down: ## Stop all Docker containers
	$(COMPOSE) down

.PHONY: docker-down-infra
docker-down-infra: ## Stop infrastructure services
	cd infrastructure && $(COMPOSE) down

.PHONY: docker-clean
docker-clean: docker-down ## Clean Docker containers, networks, and volumes
	$(COMPOSE) down -v
	cd infrastructure && $(COMPOSE) down -v

# Testing targets
.PHONY: test
test: ## Run all tests
	pytest

.PHONY: test-cov
test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=html

.PHONY: test-unit
test-unit: ## Run unit tests
	pytest -m unit

.PHONY: test-integration
test-integration: ## Run integration tests
	pytest -m integration

# Linting and formatting
.PHONY: lint
lint: ## Lint code with ruff
	ruff check src/

.PHONY: format
format: ## Format code with ruff
	ruff check src/ --fix
	ruff format src/

.PHONY: check-format
check-format: ## Check code formatting
	ruff check src/
	ruff format src/ --check

# Documentation
.PHONY: docs
docs: ## Generate documentation (placeholder)
	@echo "Documentation generation would go here"

# Cleanup
.PHONY: clean
clean: ## Clean temporary files
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf src/**/__pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf *.log
	rm -rf logs/