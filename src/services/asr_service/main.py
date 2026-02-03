import asyncio
import logging
import os
from concurrent import futures
import grpc
from grpc_reflection.v1alpha import reflection

from voice_assistant.infrastructure.grpc.generated import audio_pb2, audio_pb2_grpc
from voice_assistant.infrastructure.grpc.asr_servicer import ASRServiceServicer
from voice_assistant.application.use_cases.asr_use_cases import (
    TranscribeAudioUseCase,
    ManageASRSessionUseCase
)
from voice_assistant.infrastructure.resilience.circuit_breaker import CircuitBreaker
from voice_assistant.infrastructure.plugins.mock_asr_plugin import MockASRPlugin
from voice_assistant.infrastructure.container.service_containers import create_asr_service_container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_asr_plugins(container):
    """Initialize ASR plugins using the dependency injection container."""
    primary_asr = None
    fallback_asr = None

    try:
        # Try to get ASR plugins from container
        plugin_manager = container.resolve('plugin_manager')

        # Get primary ASR plugin
        try:
            primary_asr = plugin_manager.get_asr_plugin()
            if primary_asr:
                logger.info(f"Primary ASR plugin loaded: {type(primary_asr).__name__}")
            else:
                logger.warning("No primary ASR plugin found, using mock")
                primary_asr = MockASRPlugin()
        except Exception as e:
            logger.warning(f"Could not get ASR plugin from plugin manager: {e}")
            primary_asr = MockASRPlugin()

        # Get fallback ASR plugin if available
        # For now, using mock as fallback if no other plugin is available
        try:
            fallback_asr = MockASRPlugin()
            logger.info("Fallback ASR plugin loaded: MockASRPlugin")
        except Exception as e:
            logger.warning(f"Could not initialize fallback ASR plugin: {e}")
            fallback_asr = MockASRPlugin()

    except Exception as e:
        logger.warning(f"Failed to initialize ASR plugins from container: {e}")
        # Fallback to mock plugin
        primary_asr = MockASRPlugin()
        fallback_asr = MockASRPlugin()

    return primary_asr, fallback_asr


async def serve():
    """Start the gRPC ASR service."""
    # Create ASR service container
    asr_container = create_asr_service_container()
    container = asr_container.get_container()

    # Initialize plugins using container
    primary_asr, fallback_asr = initialize_asr_plugins(asr_container)

    # If plugins weren't properly loaded, try to load them directly
    if not primary_asr:
        # Attempt to load plugins directly using plugin registration
        try:
            from plugins.asr_vosk.registration import VoskAsrPluginRegistration
            config = {
                "model_path": os.getenv("VOSK_MODEL_PATH", "/models/vosk-model-ru-0.42"),
                "sample_rate": int(os.getenv("ASR_SAMPLE_RATE", "8000")),
                "partial_results": True
            }
            VoskAsrPluginRegistration.register(container, config)
            primary_asr = container.resolve('IAsrService')
            logger.info("Vosk ASR plugin loaded via direct registration")
        except Exception as e:
            logger.warning(f"Could not load Vosk ASR plugin: {e}")
            primary_asr = MockASRPlugin()

    # Create circuit breakers
    primary_circuit_breaker = CircuitBreaker(
        failure_threshold=int(os.getenv("PRIMARY_ASR_FAILURE_THRESHOLD", "3")),
        timeout=int(os.getenv("PRIMARY_ASR_TIMEOUT", "30")),
        name="Primary ASR"
    )

    fallback_circuit_breaker = None
    if fallback_asr:
        fallback_circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv("FALLBACK_ASR_FAILURE_THRESHOLD", "3")),
            timeout=int(os.getenv("FALLBACK_ASR_TIMEOUT", "30")),
            name="Fallback ASR"
        )

    # Create use cases using the plugins we loaded
    transcribe_use_case = TranscribeAudioUseCase(
        primary_asr=primary_asr,
        fallback_asr=fallback_asr,
        primary_circuit_breaker=primary_circuit_breaker,
        fallback_circuit_breaker=fallback_circuit_breaker,
        confidence_threshold=float(os.getenv("ASR_CONFIDENCE_THRESHOLD", "0.7"))
    )

    manage_session_use_case = ManageASRSessionUseCase(
        primary_asr=primary_asr,
        fallback_asr=fallback_asr
    )

    # Create gRPC server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    # Create servicer
    asr_servicer = ASRServiceServicer(
        transcribe_use_case=transcribe_use_case,
        manage_session_use_case=manage_session_use_case
    )

    # Add servicer to server
    audio_pb2_grpc.add_ASRServiceServicer_to_server(asr_servicer, server)

    # Enable gRPC reflection for external tools (grpcui, grpcurl)
    SERVICE_NAMES = (
        audio_pb2.DESCRIPTOR.services_by_name['ASRService'].full_name,
        reflection.SERVICE_NAME,  # Add the reflection service itself
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info("gRPC reflection enabled for ASR Service")

    # Configure server
    listen_addr = f"0.0.0.0:{os.getenv('ASR_SERVICE_PORT', '50051')}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting ASR Service on {listen_addr}")

    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down ASR Service...")
        await server.stop(5)


if __name__ == "__main__":
    asyncio.run(serve())
