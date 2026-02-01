"""
Storage Proxy Service for the voice assistant core.
Provides data persistence via gRPC with PostgreSQL backend.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""
import asyncio
import logging
import grpc
from grpc_reflection.v1alpha import reflection
from typing import AsyncGenerator
from concurrent import futures
from datetime import datetime
from uuid import UUID
import sys
import os

# Add the project root to the path to import voice_assistant modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from voice_assistant.infrastructure.grpc.generated import storage_pb2
from voice_assistant.infrastructure.grpc.generated import storage_pb2_grpc
from voice_assistant.domain.repositories.shopping_repository import IShoppingRepository
from voice_assistant.domain.repositories.reminder_repository import IReminderRepository
from voice_assistant.domain.entities.shopping_list import ShoppingList, ShoppingListItem
from voice_assistant.domain.entities.reminder import Reminder
from voice_assistant.domain.value_objects.priority import Priority
from .container import get_container, StorageServiceContainer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageServicer(storage_pb2_grpc.StorageServiceServicer):
    """gRPC servicer implementation for Storage Proxy service"""

    def __init__(self, container: StorageServiceContainer):
        self._container = container
        self._shopping_repo: IShoppingRepository = container.get_shopping_repository()
        self._reminder_repo: IReminderRepository = container.get_reminder_repository()
        logger.info("StorageServicer initialized")

    async def SaveShoppingList(self, request, context):
        """Save shopping list with items"""
        try:
            logger.info(f"Saving shopping list for session {request.session_id}")
            
            # Convert request to domain entity
            items = []
            for item_proto in request.items:
                item = ShoppingListItem.create(
                    name=item_proto.name,
                    quantity=item_proto.quantity,
                    unit=item_proto.unit if item_proto.unit else None,
                    priority=Priority(item_proto.priority) if item_proto.priority else Priority.NORMAL
                )
                items.append(item)
            
            shopping_list = ShoppingList(
                session_id=UUID(request.session_id),
                items=items
            )
            
            # Save via repository
            await self._shopping_repo.save(shopping_list)
            
            return storage_pb2.SaveResponse(
                success=True,
                message="Shopping list saved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error saving shopping list: {e}")
            return storage_pb2.SaveResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def GetShoppingList(self, request, context):
        """Get shopping list by session ID"""
        try:
            logger.info(f"Getting shopping list for session {request.session_id}")
            
            shopping_list = await self._shopping_repo.get_by_session(
                UUID(request.session_id)
            )
            
            if not shopping_list:
                return storage_pb2.ShoppingListResponse(
                    success=False,
                    message="Shopping list not found"
                )
            
            # Convert to protobuf
            items = []
            for item in shopping_list.items:
                items.append(storage_pb2.ShoppingItem(
                    id=str(item.id),
                    name=item.name,
                    quantity=item.quantity,
                    unit=item.unit or "",
                    priority=item.priority.value
                ))
            
            return storage_pb2.ShoppingListResponse(
                success=True,
                session_id=request.session_id,
                items=items
            )
            
        except Exception as e:
            logger.error(f"Error getting shopping list: {e}")
            return storage_pb2.ShoppingListResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def AddShoppingItem(self, request, context):
        """Add item to shopping list"""
        try:
            logger.info(f"Adding item to shopping list {request.session_id}")
            
            item = ShoppingListItem.create(
                name=request.item.name,
                quantity=request.item.quantity,
                unit=request.item.unit if request.item.unit else None,
                priority=Priority(request.item.priority) if request.item.priority else Priority.NORMAL
            )
            
            await self._shopping_repo.add_item(
                UUID(request.session_id),
                item
            )
            
            return storage_pb2.SaveResponse(
                success=True,
                message="Item added successfully"
            )
            
        except Exception as e:
            logger.error(f"Error adding shopping item: {e}")
            return storage_pb2.SaveResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def RemoveShoppingItem(self, request, context):
        """Remove item from shopping list"""
        try:
            logger.info(f"Removing item {request.item_id} from shopping list")
            
            success = await self._shopping_repo.remove_item(
                UUID(request.session_id),
                UUID(request.item_id)
            )
            
            return storage_pb2.SaveResponse(
                success=success,
                message="Item removed" if success else "Item not found"
            )
            
        except Exception as e:
            logger.error(f"Error removing shopping item: {e}")
            return storage_pb2.SaveResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def SaveReminder(self, request, context):
        """Save reminder"""
        try:
            logger.info(f"Saving reminder for session {request.session_id}")
            
            reminder = Reminder.create(
                session_id=UUID(request.session_id),
                description=request.description,
                reminder_date=datetime.fromtimestamp(request.reminder_timestamp),
                location=request.location if request.location else None,
                repeat_interval=request.repeat_interval if request.repeat_interval else None
            )
            
            await self._reminder_repo.save(reminder)
            
            return storage_pb2.SaveResponse(
                success=True,
                message="Reminder saved successfully",
                id=str(reminder.id)
            )
            
        except Exception as e:
            logger.error(f"Error saving reminder: {e}")
            return storage_pb2.SaveResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def GetReminders(self, request, context):
        """Get reminders for session with optional date range"""
        try:
            logger.info(f"Getting reminders for session {request.session_id}")
            
            # Parse date range if provided
            date_start = None
            date_end = None
            
            if request.date_range_start:
                date_start = datetime.fromtimestamp(request.date_range_start)
            if request.date_range_end:
                date_end = datetime.fromtimestamp(request.date_range_end)
            
            reminders = await self._reminder_repo.get_by_session(
                UUID(request.session_id),
                date_start,
                date_end
            )
            
            # Convert to protobuf
            reminder_protos = []
            for reminder in reminders:
                reminder_protos.append(storage_pb2.Reminder(
                    id=str(reminder.id),
                    session_id=str(reminder.session_id),
                    description=reminder.description,
                    reminder_timestamp=int(reminder.reminder_date.timestamp()),
                    location=reminder.location or "",
                    repeat_interval=reminder.repeat_interval or "",
                    created_at=int(reminder.created_at.timestamp()),
                    notified=reminder.notified
                ))
            
            return storage_pb2.RemindersResponse(
                success=True,
                reminders=reminder_protos
            )
            
        except Exception as e:
            logger.error(f"Error getting reminders: {e}")
            return storage_pb2.RemindersResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def DeleteReminder(self, request, context):
        """Delete reminder by ID"""
        try:
            logger.info(f"Deleting reminder {request.reminder_id}")
            
            await self._reminder_repo.delete(UUID(request.reminder_id))
            
            return storage_pb2.SaveResponse(
                success=True,
                message="Reminder deleted"
            )
            
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}")
            return storage_pb2.SaveResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def GetUpcomingReminders(self, request, context):
        """Get upcoming reminders within specified minutes"""
        try:
            logger.info(f"Getting upcoming reminders for session {request.session_id}")
            
            reminders = await self._reminder_repo.get_upcoming(
                UUID(request.session_id),
                within_minutes=request.within_minutes
            )
            
            # Convert to protobuf
            reminder_protos = []
            for reminder in reminders:
                reminder_protos.append(storage_pb2.Reminder(
                    id=str(reminder.id),
                    session_id=str(reminder.session_id),
                    description=reminder.description,
                    reminder_timestamp=int(reminder.reminder_date.timestamp()),
                    location=reminder.location or "",
                    repeat_interval=reminder.repeat_interval or "",
                    created_at=int(reminder.created_at.timestamp()),
                    notified=reminder.notified
                ))
            
            return storage_pb2.RemindersResponse(
                success=True,
                reminders=reminder_protos
            )
            
        except Exception as e:
            logger.error(f"Error getting upcoming reminders: {e}")
            return storage_pb2.RemindersResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def MarkReminderNotified(self, request, context):
        """Mark reminder as notified"""
        try:
            logger.info(f"Marking reminder {request.reminder_id} as notified")
            
            await self._reminder_repo.mark_as_notified(UUID(request.reminder_id))
            
            return storage_pb2.SaveResponse(
                success=True,
                message="Reminder marked as notified"
            )
            
        except Exception as e:
            logger.error(f"Error marking reminder as notified: {e}")
            return storage_pb2.SaveResponse(
                success=False,
                message=f"Error: {str(e)}"
            )


async def serve():
    """Start the gRPC Storage service"""
    # Create gRPC server
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
        ]
    )
    
    # Initialize container and database
    container = get_container()
    await container.initialize()
    
    # Add the servicer to the server
    storage_servicer = StorageServicer(container)
    storage_pb2_grpc.add_StorageServiceServicer_to_server(storage_servicer, server)

    # Enable gRPC reflection for external tools (grpcui, grpcurl)
    SERVICE_NAMES = (
        storage_pb2.DESCRIPTOR.services_by_name['StorageService'].full_name,
        reflection.SERVICE_NAME,  # Add the reflection service itself
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info("gRPC reflection enabled for Storage Service")

    # Listen on port 50055
    server.add_insecure_port('[::]:50055')
    
    logger.info("Starting Storage service on port 50055...")
    
    try:
        await server.start()
        logger.info("Storage service started successfully")
        
        # Keep the server running
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Storage service...")
        await container.shutdown()
        await server.stop(grace=5)
    except Exception as e:
        logger.error(f"Error running Storage service: {e}")
        await container.shutdown()
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Storage service interrupted by user")
    except Exception as e:
        logger.error(f"Storage service error: {e}")
