"""
Notification Worker service with RabbitMQ consumer.

Business concept: Async worker that consumes notification events from RabbitMQ
and delivers them via Telegram with retry logic and status tracking.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...voice_assistant.domain.entities.notification import (
    Notification, NotificationStatus, NotificationChannel
)
from ...voice_assistant.domain.repositories.notification_repository import INotificationRepository
from ...voice_assistant.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from ...voice_assistant.infrastructure.external.telegram_client import (
    TelegramClient, TelegramError, TelegramAPIError
)

logger = logging.getLogger(__name__)


class NotificationWorker:
    """
    Worker that processes notification events from RabbitMQ.
    
    Features:
    - Consumes notification events from RabbitMQ queue
    - Delivers notifications via Telegram
    - Tracks delivery status in database
    - Implements retry logic with exponential backoff
    - Handles delivery failures gracefully
    """
    
    def __init__(
        self,
        rabbitmq_client: RabbitMQClient,
        notification_repository: INotificationRepository,
        telegram_client: Optional[TelegramClient] = None,
        queue_name: str = "notifications",
        routing_keys: Optional[list] = None
    ):
        self._rabbitmq = rabbitmq_client
        self._repository = notification_repository
        self._telegram = telegram_client
        self._queue_name = queue_name
        self._routing_keys = routing_keys or ["notification.*", "reminder.due"]
        self._consumer_tag: Optional[str] = None
        self._is_running = False
    
    async def start(self) -> bool:
        """
        Start the notification worker.
        
        Returns:
            True if worker started successfully
        """
        if self._is_running:
            logger.warning("Notification worker is already running")
            return True
        
        try:
            # Ensure RabbitMQ is connected
            if not await self._rabbitmq.ensure_connected():
                logger.error("Cannot start worker: RabbitMQ not connected")
                return False
            
            # Start consuming messages
            self._consumer_tag = await self._rabbitmq.consume(
                queue_name=self._queue_name,
                callback=self._process_message,
                routing_keys=self._routing_keys,
                durable=True,
                auto_ack=False
            )
            
            if self._consumer_tag:
                self._is_running = True
                logger.info(f"Notification worker started with consumer tag: {self._consumer_tag}")
                return True
            else:
                logger.error("Failed to start consumer")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start notification worker: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the notification worker"""
        if not self._is_running:
            return
        
        try:
            if self._consumer_tag:
                await self._rabbitmq.cancel_consumer(self._consumer_tag)
                self._consumer_tag = None
            
            self._is_running = False
            logger.info("Notification worker stopped")
            
        except Exception as e:
            logger.error(f"Error stopping notification worker: {e}")
    
    async def _process_message(self, message_data: Dict[str, Any]) -> None:
        """
        Process a notification message from RabbitMQ.
        
        This is the main message handler that:
        1. Parses the notification event
        2. Creates/updates notification record
        3. Attempts delivery via Telegram
        4. Updates delivery status
        """
        try:
            logger.debug(f"Processing notification message: {message_data}")
            
            # Extract message type and data
            message_type = message_data.get('type', 'generic')
            data = message_data.get('data', {})
            
            # Handle different message types
            if message_type == 'notification.telegram':
                await self._handle_telegram_notification(data)
            elif message_type == 'reminder.due':
                await self._handle_reminder_notification(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing notification message: {e}")
            # Don't re-raise - let RabbitMQ handle retry via reject/requeue
    
    async def _handle_telegram_notification(self, data: Dict[str, Any]) -> None:
        """Handle Telegram notification"""
        recipient_id = data.get('recipient_id')
        message = data.get('message')
        notification_id = data.get('notification_id')
        metadata = data.get('metadata', {})
        
        if not recipient_id or not message:
            logger.error("Missing required fields for Telegram notification")
            return
        
        # Create or get notification record
        if notification_id:
            notification = await self._repository.get_by_id(notification_id)
        else:
            notification = Notification.create(
                recipient_id=recipient_id,
                channel=NotificationChannel.TELEGRAM,
                message=message,
                metadata=metadata
            )
            await self._repository.save(notification)
        
        if not notification:
            logger.error(f"Notification not found: {notification_id}")
            return
        
        # Attempt delivery
        await self._deliver_notification(notification)
    
    async def _handle_reminder_notification(self, data: Dict[str, Any]) -> None:
        """Handle reminder due notification"""
        reminder_id = data.get('reminder_id')
        user_id = data.get('user_id')
        recipient_id = data.get('recipient_id')  # Telegram chat ID
        description = data.get('description', 'Reminder')
        
        if not recipient_id:
            logger.error("Missing recipient_id for reminder notification")
            return
        
        # Format reminder message
        message = f"🔔 <b>Reminder</b>\n\n{description}"
        
        # Create notification
        notification = Notification.create(
            recipient_id=recipient_id,
            channel=NotificationChannel.TELEGRAM,
            message=message,
            metadata={
                'reminder_id': reminder_id,
                'user_id': user_id,
                'type': 'reminder'
            }
        )
        
        await self._repository.save(notification)
        
        # Attempt delivery
        await self._deliver_notification(notification)
    
    async def _deliver_notification(self, notification: Notification) -> None:
        """
        Deliver a notification via Telegram with retry logic.
        
        Implements exponential backoff for transient failures.
        """
        if not self._telegram:
            logger.error("Telegram client not configured")
            notification.mark_as_failed("Telegram client not configured")
            await self._repository.save(notification)
            return
        
        # Check if we can retry
        if not notification.can_retry():
            logger.warning(f"Notification {notification.id} exceeded max retries")
            notification.mark_as_failed("Max retries exceeded")
            await self._repository.save(notification)
            return
        
        try:
            # Attempt to send message
            result = await self._telegram.send_notification(
                recipient_id=notification.recipient_id,
                message=notification.message,
                metadata=notification.metadata
            )
            
            # Extract message ID from result
            message_info = result.get('result', {})
            external_message_id = str(message_info.get('message_id'))
            
            # Mark as sent/delivered
            notification.mark_as_sent(external_message_id=external_message_id)
            notification.mark_as_delivered()
            
            await self._repository.save(notification)
            
            logger.info(
                f"Notification {notification.id} delivered successfully. "
                f"Telegram message ID: {external_message_id}"
            )
            
        except TelegramAPIError as e:
            # API error - may be retryable
            logger.error(f"Telegram API error for notification {notification.id}: {e}")
            await self._handle_delivery_failure(notification, str(e))
            
        except TelegramError as e:
            # Other Telegram error
            logger.error(f"Telegram error for notification {notification.id}: {e}")
            await self._handle_delivery_failure(notification, str(e))
            
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error delivering notification {notification.id}: {e}")
            await self._handle_delivery_failure(notification, f"Unexpected error: {e}")
    
    async def _handle_delivery_failure(self, notification: Notification, error_message: str) -> None:
        """
        Handle delivery failure with retry logic.
        
        Implements exponential backoff before retrying.
        """
        # Increment retry count
        notification.increment_retry()
        notification.error_message = error_message
        
        await self._repository.save(notification)
        
        if notification.can_retry():
            # Calculate retry delay
            delay = notification.get_retry_delay(base_delay=2.0)
            
            logger.warning(
                f"Notification {notification.id} failed, retrying in {delay}s "
                f"(attempt {notification.retry_count}/{notification.max_retries})"
            )
            
            # Schedule retry
            asyncio.create_task(self._retry_notification(notification.id, delay))
        else:
            logger.error(
                f"Notification {notification.id} failed permanently after "
                f"{notification.retry_count} attempts"
            )
            notification.mark_as_failed(f"Failed after {notification.retry_count} attempts: {error_message}")
            await self._repository.save(notification)
    
    async def _retry_notification(self, notification_id, delay: float) -> None:
        """Retry notification delivery after delay"""
        await asyncio.sleep(delay)
        
        # Get fresh notification data
        notification = await self._repository.get_by_id(notification_id)
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found for retry")
            return
        
        if notification.is_terminal_state():
            logger.debug(f"Notification {notification_id} already in terminal state")
            return
        
        # Attempt delivery again
        await self._deliver_notification(notification)
    
    async def process_pending_notifications(self) -> int:
        """
        Process any pending notifications from database.
        
        This is useful for retrying notifications that failed
        while the worker was offline.
        
        Returns:
            Number of notifications processed
        """
        try:
            pending = await self._repository.get_pending_notifications(limit=100)
            
            logger.info(f"Processing {len(pending)} pending notifications")
            
            for notification in pending:
                await self._deliver_notification(notification)
            
            return len(pending)
            
        except Exception as e:
            logger.error(f"Error processing pending notifications: {e}")
            return 0
    
    @property
    def is_running(self) -> bool:
        """Check if worker is running"""
        return self._is_running
