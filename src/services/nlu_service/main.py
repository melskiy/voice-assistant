import asyncio
import logging
import os
import sys
from concurrent import futures
import grpc
from grpc_reflection.v1alpha import reflection
from voice_assistant.infrastructure.grpc.generated import nlu_pb2, nlu_pb2_grpc
from voice_assistant.infrastructure.grpc.nlu_servicer import NLUServiceServicer
from voice_assistant.application.use_cases.nlu_use_cases import (
    ExtractIntentUseCase,
    ProcessConfidenceUseCase
)
from voice_assistant.infrastructure.container.service_containers import create_nlu_service_container
from voice_assistant.infrastructure.plugins.plugin_manager import IoC_PluginManager

try:
    from confidence_handler import ConfidenceHandler
    CONFIDENCE_HANDLER_AVAILABLE = True
except ImportError:
    CONFIDENCE_HANDLER_AVAILABLE = False
    logging.warning("ConfidenceHandler not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_nlu_plugin(nlu_container):
    """Initialize NLU plugin using the dependency injection container."""
    nlu_plugin = None

    try:
        # Get plugin manager directly from the service container
        plugin_manager = nlu_container.plugin_manager

        # Get NLU plugin
        try:
            nlu_plugin = plugin_manager.get_nlu_plugin()
            if nlu_plugin:
                logger.info(f"NLU plugin loaded: {type(nlu_plugin).__name__}")
            else:
                logger.warning("No NLU plugin found in container")
        except Exception as e:
            logger.error(f"Could not get NLU plugin from plugin manager: {e}")

    except Exception as e:
        logger.error(f"Failed to initialize NLU plugin from container: {e}")

    return nlu_plugin


async def serve():
    """Start the gRPC NLU service."""
    # Create NLU service container
    nlu_container_obj = create_nlu_service_container()
    container = nlu_container_obj.get_container()

    # Initialize plugin using container
    nlu_plugin = initialize_nlu_plugin(nlu_container_obj)

    # If plugin wasn't properly loaded, try to load it directly
    if not nlu_plugin:
        # Attempt to load plugins directly using plugin registration
        try:
            from plugins.nlu_regex.registration import RegexNluPluginRegistration
            config = {
                "language": "ru",
                "case_sensitive": False
            }
            RegexNluPluginRegistration.register(container, config)
            nlu_plugin = container.resolve('INluService')
            logger.info("Regex NLU plugin loaded via direct registration")
        except Exception as e:
            logger.warning(f"Could not load Regex NLU plugin: {e}")
            try:
                from plugins.nlu_sklearn.registration import SklearnNluPluginRegistration
                config = {
                    "language": "ru",
                    "train_on_init": True
                }
                SklearnNluPluginRegistration.register(container, config)
                nlu_plugin = container.resolve('INluService')
                logger.info("Sklearn NLU plugin loaded via direct registration")
            except Exception as e2:
                logger.error(f"Could not load Sklearn NLU plugin: {e2}")
                nlu_plugin = None

    if not nlu_plugin:
        logger.error("No NLU plugin available, cannot start service")
        return

    # Create use cases using the plugin we loaded
    extract_intent_use_case = ExtractIntentUseCase(
        nlu_plugin=nlu_plugin,
        confidence_threshold=0.7
    )

    # Use confidence handler thresholds if available
    if CONFIDENCE_HANDLER_AVAILABLE:
        handler = ConfidenceHandler(threshold=0.7)
        process_confidence_use_case = nlu_container_obj.create_process_confidence_use_case()
    else:
        process_confidence_use_case = nlu_container_obj.create_process_confidence_use_case()

    # Create gRPC server
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
        ]
    )

    # Create servicer
    nlu_servicer = NLUServiceServicer(
        extract_intent_use_case=extract_intent_use_case,
        process_confidence_use_case=process_confidence_use_case
    )

    # Add servicer to server
    nlu_pb2_grpc.add_NLUServiceServicer_to_server(nlu_servicer, server)

    # Enable gRPC reflection for external tools (grpcui, grpcurl)
    SERVICE_NAMES = (
        nlu_pb2.DESCRIPTOR.services_by_name['NLUService'].full_name,
        reflection.SERVICE_NAME,  # Add the reflection service itself
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info("gRPC reflection enabled for NLU Service")

    # Listen on port 50052
    server.add_insecure_port('[::]:50052')

    logger.info("Starting NLU service on port 50052...")

    try:
        await server.start()
        logger.info("NLU service started successfully")
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down NLU service...")
        await server.stop(grace=5)
    except Exception as e:
        logger.error(f"Error running NLU service: {e}")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("NLU service interrupted by user")
    except Exception as e:
        logger.error(f"Failed to start NLU service: {e}")
        sys.exit(1)
