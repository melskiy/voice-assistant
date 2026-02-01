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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_tts_plugin():
    """Initialize TTS plugin."""
    tts_plugin = None
    
    # Try Silero TTS
    try:
        from plugins.tts_silero.plugin import SileroTTSPlugin
        
        config = {
            "model_id": os.getenv("TTS_SILERO_MODEL_ID", "v3_ru.pt"),
            "sample_rate": int(os.getenv("TTS_SILERO_SAMPLE_RATE", "48000")),
            "speaker": os.getenv("TTS_SILERO_SPEAKER", "baya"),
            "device": os.getenv("TTS_SILERO_DEVICE", "cpu")
        }
        
        tts_plugin = SileroTTSPlugin(config)
        logger.info("Silero TTS plugin initialized")
        
    except Exception as e:
        logger.warning(f"Failed to initialize Silero TTS: {e}")
    
    # Fallback to mock
    if not tts_plugin:
        try:
            from plugins.tts_mock.plugin import MockTTSPlugin
            tts_plugin = MockTTSPlugin()
            logger.info("Mock TTS plugin initialized as fallback")
        except Exception as e:
            logger.error(f"Failed to initialize Mock TTS: {e}")
    
    return tts_plugin


async def serve():
    """Start the gRPC TTS service."""
    # Initialize plugin
    tts_plugin = initialize_tts_plugin()
    
    if not tts_plugin:
        logger.error("No TTS plugin available, cannot start service")
        return
    
    # Create use cases
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
