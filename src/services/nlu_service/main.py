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

try:
    from confidence_handler import ConfidenceHandler
    CONFIDENCE_HANDLER_AVAILABLE = True
except ImportError:
    CONFIDENCE_HANDLER_AVAILABLE = False
    logging.warning("ConfidenceHandler not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_nlu_plugin():
    """Initialize NLU plugin."""
    nlu_plugin = None
    
    # Get configured plugin ID
    plugin_id = os.getenv("NLU_PLUGIN_ID", "nlu.sklearn")
    
    # Try to load plugin
    try:
        if plugin_id == "nlu.sklearn":
            from plugins.nlu_sklearn.plugin import SklearnNLUPlugin
            nlu_plugin = SklearnNLUPlugin({})
            logger.info("Sklearn NLU plugin initialized")
        elif plugin_id == "nlu.regex":
            from plugins.nlu_regex.plugin import RegexNLUPlugin
            nlu_plugin = RegexNLUPlugin({})
            logger.info("Regex NLU plugin initialized")
        elif plugin_id == "nlu.spacy":
            from plugins.nlu_spacy.plugin import SpacyNLUPlugin
            nlu_plugin = SpacyNLUPlugin({})
            logger.info("Spacy NLU plugin initialized")
        else:
            logger.warning(f"Unknown NLU plugin: {plugin_id}")
            
    except Exception as e:
        logger.error(f"Failed to initialize NLU plugin {plugin_id}: {e}")
    
    return nlu_plugin


async def serve():
    """Start the gRPC NLU service."""
    # Initialize plugin
    nlu_plugin = initialize_nlu_plugin()
    
    if not nlu_plugin:
        logger.error("No NLU plugin available, cannot start service")
        return
    
    # Create use cases
    extract_intent_use_case = ExtractIntentUseCase(
        nlu_plugin=nlu_plugin,
        confidence_threshold=0.7
    )
    
    # Use confidence handler thresholds if available
    if CONFIDENCE_HANDLER_AVAILABLE:
        handler = ConfidenceHandler(threshold=0.7)
        process_confidence_use_case = ProcessConfidenceUseCase(
            high_threshold=0.8,
            medium_threshold=0.6,
            low_threshold=0.4
        )
    else:
        process_confidence_use_case = ProcessConfidenceUseCase()
    
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
