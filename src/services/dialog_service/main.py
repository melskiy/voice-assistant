"""
Dialog Service - Entry point.

This module only handles service initialization and startup.
All business logic is in voice_assistant package.
"""
import asyncio
import logging
import sys
import os
from concurrent import futures

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import grpc
from grpc_reflection.v1alpha import reflection

from voice_assistant.infrastructure.grpc.generated import dialog_pb2, dialog_pb2_grpc
from voice_assistant.infrastructure.grpc.dialog_servicer import DialogServiceServicer
from voice_assistant.infrastructure.persistence.in_memory_dialog_session_repository import InMemoryDialogSessionRepository
from voice_assistant.application.use_cases.dialog_use_cases import (
    ProcessIntentUseCase,
    HandleConfirmationUseCase,
    GetDialogStateUseCase,
    ResetDialogUseCase
)
from voice_assistant.infrastructure.container.service_containers import create_dialog_service_container

# Import error recovery if available
try:
    from error_recovery import ErrorRecoveryManager
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False
    logging.warning("ErrorRecoveryManager not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def serve():
    """Start the gRPC Dialog service."""
    # Create Dialog service container
    dialog_container = create_dialog_service_container()
    container = dialog_container.get_container()

    # Create repository
    session_repo = InMemoryDialogSessionRepository()

    # Create error recovery service if available
    error_recovery = ErrorRecoveryManager() if ERROR_RECOVERY_AVAILABLE else None

    # Create use cases using container
    process_intent_use_case = dialog_container.create_process_intent_use_case(error_recovery_service=error_recovery)
    handle_confirmation_use_case = dialog_container.create_handle_confirmation_use_case()
    get_dialog_state_use_case = dialog_container.create_get_dialog_state_use_case()
    reset_dialog_use_case = dialog_container.create_reset_dialog_use_case()

    # Create gRPC server
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
        ]
    )

    # Create servicer with use cases
    dialog_servicer = DialogServiceServicer(
        process_intent_use_case=process_intent_use_case,
        handle_confirmation_use_case=handle_confirmation_use_case,
        get_dialog_state_use_case=get_dialog_state_use_case,
        reset_dialog_use_case=reset_dialog_use_case
    )

    # Add servicer to server
    dialog_pb2_grpc.add_DialogServiceServicer_to_server(dialog_servicer, server)

    # Enable gRPC reflection for external tools (grpcui, grpcurl)
    SERVICE_NAMES = (
        dialog_pb2.DESCRIPTOR.services_by_name['DialogService'].full_name,
        reflection.SERVICE_NAME,  # Add the reflection service itself
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info("gRPC reflection enabled for Dialog Service")

    # Listen on port 50053
    server.add_insecure_port('[::]:50053')

    logger.info("Starting Dialog service on port 50053...")

    try:
        await server.start()
        logger.info("Dialog service started successfully")

        # Keep the server running
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Dialog service...")
        await server.stop(grace=5)
    except Exception as e:
        logger.error(f"Error running Dialog service: {e}")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Dialog service interrupted by user")
    except Exception as e:
        logger.error(f"Failed to start Dialog service: {e}")
        sys.exit(1)
