"""
Notification Worker Service for the voice assistant core.
Provides async messaging via RabbitMQ and Telegram delivery.

User goal: Process notification events from RabbitMQ and deliver via Telegram
Success guarantee: Messages are delivered with retry and status tracking
Side effects: Updates notification status in database, sends Telegram messages

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""
import asyncio
import logging
import sys
import os
from typing import Optional
from concurrent import futures

import grpc
from grpc import aio
from grpc_reflection.v1alpha import reflection

# Add the project root to the path to import voice_assistant modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .container import get_container, NotificationServiceContainer
from .notification_worker import NotificationWorker
from voice_assistant.infrastructure.container.service_containers import create_notification_service_container

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NotificationServicer:
    """gRPC servicer for Notification service"""
    
    def __init__(self, container: NotificationServiceContainer, worker: NotificationWorker):
        self._container = container
        self._worker = worker
        logger.info("NotificationServicer initialized")
    
    async def HealthCheck(self, request, context):
        """Health check endpoint"""
        from voice_assistant.infrastructure.grpc.generated import notification_pb2
        
        is_healthy = (
            self._container.get_rabbitmq_client().is_connected and
            self._worker.is_running
        )
        
        return notification_pb2.HealthResponse(
            healthy=is_healthy,
            service="notification",
            timestamp=int(asyncio.get_event_loop().time())
        )
    
    async def GetStatus(self, request, context):
        """Get notification service status"""
        from voice_assistant.infrastructure.grpc.generated import notification_pb2
        
        rabbitmq_status = "connected" if self._container.get_rabbitmq_client().is_connected else "disconnected"
        worker_status = "running" if self._worker.is_running else "stopped"
        
        telegram_client = self._container.get_telegram_client()
        telegram_status = "configured" if telegram_client else "not_configured"
        
        return notification_pb2.StatusResponse(
            rabbitmq_status=rabbitmq_status,
            worker_status=worker_status,
            telegram_status=telegram_status,
            timestamp=int(asyncio.get_event_loop().time())
        )


async def serve():
    """Start the Notification Worker service"""
    # Create Notification service container
    notification_container = create_notification_service_container()
    app_container = notification_container.get_container()

    # Create gRPC server
    server = aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
        ]
    )

    # Initialize container
    container = get_container()

    try:
        await container.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize container: {e}")
        # Continue anyway - some components might work

    # Create notification worker
    worker = NotificationWorker(
        rabbitmq_client=container.get_rabbitmq_client(),
        notification_repository=container.get_notification_repository(),
        telegram_client=container.get_telegram_client(),
        queue_name=os.getenv('NOTIFICATION_QUEUE_NAME', 'notifications'),
        routing_keys=['notification.*', 'reminder.due']
    )

    # Start the worker
    worker_started = await worker.start()
    if not worker_started:
        logger.warning("Failed to start notification worker immediately, will retry")

    # Process any pending notifications from database
    try:
        processed = await worker.process_pending_notifications()
        logger.info(f"Processed {processed} pending notifications from database")
    except Exception as e:
        logger.error(f"Error processing pending notifications: {e}")

    # Add the servicer to the server
    # Note: We're creating a simple servicer without protobuf for now
    # In production, you would generate notification_pb2 from a .proto file

    # Enable gRPC reflection for external tools (grpcui, grpcurl)
    # Note: When notification.proto is available, add the service name:
    # SERVICE_NAMES = (
    #     notification_pb2.DESCRIPTOR.services_by_name['NotificationService'].full_name,
    #     reflection.SERVICE_NAME,
    # )
    # For now, we only enable the reflection service itself
    SERVICE_NAMES = (reflection.SERVICE_NAME,)
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info("gRPC reflection enabled for Notification Service (basic mode)")

    # Listen on port 50056
    server.add_insecure_port('[::]:50056')

    logger.info("Starting Notification Worker service on port 50056...")

    try:
        await server.start()
        logger.info("Notification Worker service started successfully")

        # Keep the server running
        await server.wait_for_termination()

    except KeyboardInterrupt:
        logger.info("Shutting down Notification Worker service...")
    except Exception as e:
        logger.error(f"Error running Notification Worker service: {e}")
    finally:
        # Stop worker
        await worker.stop()

        # Shutdown container
        await container.shutdown()

        # Stop server
        await server.stop(grace=5)

        logger.info("Notification Worker service shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Notification Worker service interrupted by user")
    except Exception as e:
        logger.error(f"Notification Worker service error: {e}")
