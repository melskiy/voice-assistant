"""
Gateway Service for Voice Assistant.

This module provides the main entry point for the Gateway Service with a clean
architecture that delegates all route handling to modular viewsets.

Architecture:
- main.py: Minimal initialization and application lifecycle management
- views/: Modular viewsets for each API resource (decorator-registered)
- schemas/: Pydantic models for request/response validation
- services/: Business logic services used by views

Usage:
    python -m src.services.gateway_service.main

    Or with uvicorn:
    uvicorn src.services.gateway_service.main:app --host 0.0.0.0 --port 8000
"""
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI

# Import view registry and viewsets (auto-registered via decorators)
from voice_assistant.presentation.views import ViewRegistry

# Import services
from voice_assistant.application.services.audio_stream_manager import AudioStreamManager
from voice_assistant.infrastructure.cache.session_cache import SessionCache
from voice_assistant.interfaces.container import Config
from voice_assistant.infrastructure.container.service_containers import create_gateway_service_container

# Note: PluginService is intentionally NOT imported here.
# Plugins are loaded by their respective microservices (ASR/NLU/TTS),
# not by the Gateway Service which acts as a lightweight API gateway.

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def initialize_redis(config: Config) -> redis.Redis:
    """
    Initialize Redis connection.
    
    Args:
        config: Application configuration
        
    Returns:
        Redis client instance
        
    Raises:
        RuntimeError: If Redis connection fails
    """
    redis_client = redis.from_url(config.redis_url, decode_responses=False)
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        await redis_client.aclose()
        raise RuntimeError(f"Redis connection failed: {e}")


async def initialize_audio_manager(config: Config) -> AudioStreamManager:
    """
    Initialize audio stream manager.
    
    Args:
        config: Application configuration
        
    Returns:
        Initialized audio stream manager
    """
    audio_manager = AudioStreamManager(config)
    
    # Try to connect to ASR service (non-blocking)
    try:
        asr_connected = await audio_manager.initialize_asr_connection(config.asr_service_url)
        if asr_connected:
            logger.info("ASR service connected")
        else:
            logger.warning("ASR service not available - audio processing will be limited")
    except Exception as e:
        logger.warning(f"ASR service connection failed: {e}")
    
    return audio_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup initialization and graceful shutdown.
    """
    logger.info("=" * 50)
    logger.info("Starting Gateway Service...")
    logger.info("=" * 50)

    # Create Gateway service container
    gateway_container = create_gateway_service_container()
    container = gateway_container.get_container()

    # Initialize configuration
    config = Config()

    # Initialize Redis
    redis_client = await initialize_redis(config)

    # Initialize session cache
    session_cache = SessionCache(redis_client, config.session_timeout_minutes * 60)

    # Initialize audio stream manager (uses gRPC to connect to ASR/NLU/TTS services)
    audio_stream_manager = await initialize_audio_manager(config)

    # Note: PluginService is NOT initialized here.
    # Plugins (ASR/NLU/TTS) are loaded by their respective microservices via gRPC.
    # Gateway Service acts as a lightweight API gateway only.

    # Store in app state for access by views
    app.state.config = config
    app.state.redis_client = redis_client
    app.state.session_cache = session_cache
    app.state.audio_stream_manager = audio_stream_manager

    # Initialize all registered viewsets
    dependencies = {
        "config": config,
        "redis_client": redis_client,
        "session_cache": session_cache,
        "audio_stream_manager": audio_stream_manager,
    }

    viewset_instances = ViewRegistry.create_all(app, base_prefix="/v1", **dependencies)
    logger.info(f"Initialized {len(viewset_instances)} viewsets")

    logger.info("=" * 50)
    logger.info("Gateway Service started successfully")
    logger.info("=" * 50)

    yield  # Application runs here

    # Shutdown sequence
    logger.info("=" * 50)
    logger.info("Shutting down Gateway Service...")
    logger.info("=" * 50)

    try:
        # Close audio connections (gRPC connections to ASR/NLU/TTS services)
        if hasattr(app.state, 'audio_stream_manager'):
            await app.state.audio_stream_manager.close_connections()

        # Close Redis connection
        if hasattr(app.state, 'redis_client'):
            await app.state.redis_client.aclose()

        logger.info("Gateway Service shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        # Clear view registry instances
        ViewRegistry._instances.clear()


# Create FastAPI application
app = FastAPI(
    title="Voice Assistant Gateway Service",
    description="API Gateway for Voice Assistant - handles calls, audio processing, and integrations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Application metadata for health checks
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "service": "Voice Assistant Gateway",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn when executed directly
    uvicorn.run(
        "src.services.gateway_service.main:app",
        host="0.0.0.0",
        port=int(os.getenv('GATEWAY_SERVICE_PORT', '8000')),
        reload=False,
        log_level="info"
    )