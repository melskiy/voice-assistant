"""
TTS Service - Entry point.

This module only handles service initialization and startup.
All business logic is in voice_assistant package.
"""
import asyncio
import logging
import os
import sys
from concurrent import futures

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import grpc
from grpc_reflection.v1alpha import reflection

from voice_assistant.infrastructure.grpc.generated import tts_pb2, tts_pb2_grpc
from voice_assistant.infrastructure.grpc.tts_servicer import TTSServiceServicer
from voice_assistant.application.use_cases.tts_use_cases import (
    SynthesizeSpeechUseCase,
    GetAvailableVoicesUseCase
)
from voice_assistant.domain.services.text_normalizer import RussianTextNormalizer
from voice_assistant.infrastructure.plugins.plugin_interface import TTSPlugin
from voice_assistant.infrastructure.container.service_containers import create_tts_service_container
from voice_assistant.infrastructure.plugins.plugin_manager import IoC_PluginManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_tts_plugin(tts_container):
    """Initialize TTS plugin using the dependency injection container."""
    tts_plugin = None

    try:
        # Get plugin manager directly from the service container
        plugin_manager = tts_container.plugin_manager

        # Get TTS plugin
        try:
            tts_plugin = plugin_manager.get_tts_plugin()
            if tts_plugin:
                logger.info(f"TTS plugin loaded: {type(tts_plugin).__name__}")
            else:
                logger.warning("No TTS plugin found in container")
        except Exception as e:
            logger.error(f"Could not get TTS plugin from plugin manager: {e}")

    except Exception as e:
        logger.error(f"Failed to initialize TTS plugin from container: {e}")

    return tts_plugin


async def serve():
    """Start the gRPC TTS service."""
    # Create TTS service container
    tts_container_obj = create_tts_service_container()
    container = tts_container_obj.get_container()

    # Initialize plugin using container
    tts_plugin = initialize_tts_plugin(tts_container_obj)

    # If plugin wasn't properly loaded, try to load it directly
    if not tts_plugin:
        # Attempt to load plugins directly using plugin registration
        try:
            from plugins.tts_silero.registration import SileroTtsPluginRegistration
            config = {
                "model_id": os.getenv("TTS_SILERO_MODEL_ID", "v3_ru.pt"),
                "sample_rate": int(os.getenv("TTS_SILERO_SAMPLE_RATE", "48000")),
                "speaker": os.getenv("TTS_SILERO_SPEAKER", "baya"),
                "device": os.getenv("TTS_SILERO_DEVICE", "cpu")
            }
            SileroTtsPluginRegistration.register(container, config)
            tts_plugin = container.resolve('ITtsService')
            logger.info("Silero TTS plugin loaded via direct registration")
        except Exception as e:
            logger.warning(f"Could not load Silero TTS plugin: {e}")
            try:
                from plugins.tts_mock.registration import MockTtsPluginRegistration
                config = {
                    "delay_ms": 100
                }
                MockTtsPluginRegistration.register(container, config)
                tts_plugin = container.resolve('ITtsService')
                logger.info("Mock TTS plugin loaded via direct registration")
            except Exception as e2:
                logger.error(f"Could not load Mock TTS plugin: {e2}")
                tts_plugin = None

    if not tts_plugin:
        logger.error("No TTS plugin available, cannot start service")
        return

    # Create use cases using the plugin we loaded
    synthesize_use_case = SynthesizeSpeechUseCase(
        tts_plugin=tts_plugin,
        text_normalizer=RussianTextNormalizer()
    )
    get_voices_use_case = GetAvailableVoicesUseCase()

    # Create gRPC server
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
        ]
    )

    # Create servicer
    tts_servicer = TTSServiceServicer(
        synthesize_use_case=synthesize_use_case,
        get_voices_use_case=get_voices_use_case
    )

    # Add servicer to server
    tts_pb2_grpc.add_TTSServiceServicer_to_server(tts_servicer, server)

    # Enable gRPC reflection for external tools (grpcui, grpcurl)
    SERVICE_NAMES = (
        tts_pb2.DESCRIPTOR.services_by_name['TTSService'].full_name,
        reflection.SERVICE_NAME,  # Add the reflection service itself
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info("gRPC reflection enabled for TTS Service")

    # Listen on port 50054
    server.add_insecure_port('[::]:50054')

    logger.info("Starting TTS service on port 50054...")

    try:
        await server.start()
        logger.info("TTS service started successfully")
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down TTS service...")
        await server.stop(grace=5)
    except Exception as e:
        logger.error(f"Error running TTS service: {e}")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("TTS service interrupted by user")
    except Exception as e:
        logger.error(f"TTS service error: {e}")
        sys.exit(1)
