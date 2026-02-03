"""
Tests for Notification Worker service.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""
import asyncio
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from voice_assistant.domain.entities.notification import (
    Notification, NotificationStatus, NotificationChannel
)
from voice_assistant.domain.repositories.notification_repository import INotificationRepository
from voice_assistant.infrastructure.messaging.rabbitmq_client import RabbitMQClient, RabbitMQConfig
from voice_assistant.infrastructure.external.telegram_client import (
    TelegramClient, TelegramConfig, TelegramAPIError
)
from services.notification_service.notification_worker import NotificationWorker


class MockNotificationRepository(INotificationRepository):
    """Mock implementation for testing"""
    
    def __init__(self):
        self._notifications = {}
    
    async def save(self, notification: Notification) -> None:
        self._notifications[notification.id] = notification
    
    async def get_by_id(self, notification_id):
        return self._notifications.get(notification_id)
    
    async def get_by_recipient(self, recipient_id, status=None, limit=100):
        result = []
        for n in self._notifications.values():
            if n.recipient_id == recipient_id:
                if status is None or n.status == status:
                    result.append(n)
        return result[:limit]
    
    async def get_pending_notifications(self, limit=100):
        return [
            n for n in self._notifications.values()
            if n.status in (NotificationStatus.PENDING, NotificationStatus.RETRYING)
        ][:limit]
    
    async def get_failed_notifications(self, max_retries=5, limit=100):
        return [
            n for n in self._notifications.values()
            if n.status == NotificationStatus.FAILED and n.retry_count < max_retries
        ][:limit]
    
    async def update_status(self, notification_id, status, error_message=None, external_message_id=None):
        n = self._notifications.get(notification_id)
        if n:
            n.status = status
            if error_message:
                n.error_message = error_message
            if external_message_id:
                n.external_message_id = external_message_id
    
    async def increment_retry_count(self, notification_id):
        n = self._notifications.get(notification_id)
        if n:
            n.retry_count += 1
    
    async def delete_old_notifications(self, before_date):
        to_delete = [
            k for k, v in self._notifications.items()
            if v.created_at < before_date
        ]
        for k in to_delete:
            del self._notifications[k]
        return len(to_delete)


@pytest.fixture
def mock_repository():
    return MockNotificationRepository()


@pytest.fixture
def mock_rabbitmq():
    client = MagicMock(spec=RabbitMQClient)
    client.is_connected = True
    client.ensure_connected = AsyncMock(return_value=True)
    client.consume = AsyncMock(return_value="consumer-tag-123")
    client.cancel_consumer = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_telegram():
    client = MagicMock(spec=TelegramClient)
    client.send_notification = AsyncMock(return_value={
        'ok': True,
        'result': {'message_id': 12345}
    })
    return client


@pytest.fixture
def worker(mock_rabbitmq, mock_repository, mock_telegram):
    return NotificationWorker(
        rabbitmq_client=mock_rabbitmq,
        notification_repository=mock_repository,
        telegram_client=mock_telegram,
        queue_name="test_notifications"
    )


@pytest.mark.asyncio
async def test_worker_start_stop(worker, mock_rabbitmq):
    """Test worker start and stop lifecycle"""
    # Start worker
    started = await worker.start()
    assert started is True
    assert worker.is_running is True
    mock_rabbitmq.consume.assert_called_once()
    
    # Stop worker
    await worker.stop()
    assert worker.is_running is False
    mock_rabbitmq.cancel_consumer.assert_called_once()


@pytest.mark.asyncio
async def test_notification_delivery_success(worker, mock_repository, mock_telegram):
    """Test successful notification delivery"""
    # Create notification
    notification = Notification.create(
        recipient_id="123456789",
        channel=NotificationChannel.TELEGRAM,
        message="Test message"
    )
    await mock_repository.save(notification)
    
    # Deliver notification
    await worker._deliver_notification(notification)
    
    # Verify Telegram was called
    mock_telegram.send_notification.assert_called_once()
    
    # Verify notification status updated
    updated = await mock_repository.get_by_id(notification.id)
    assert updated.status == NotificationStatus.DELIVERED
    assert updated.external_message_id == "12345"


@pytest.mark.asyncio
async def test_notification_delivery_failure_with_retry(worker, mock_repository, mock_telegram):
    """Test notification delivery failure with retry"""
    # Mock Telegram to fail
    mock_telegram.send_notification.side_effect = TelegramAPIError(400, "Bad Request")
    
    # Create notification
    notification = Notification.create(
        recipient_id="123456789",
        channel=NotificationChannel.TELEGRAM,
        message="Test message"
    )
    await mock_repository.save(notification)
    
    # Deliver notification
    await worker._deliver_notification(notification)
    
    # Verify notification status updated to retrying
    updated = await mock_repository.get_by_id(notification.id)
    assert updated.status == NotificationStatus.RETRYING
    assert updated.retry_count == 1
    assert updated.error_message is not None


@pytest.mark.asyncio
async def test_notification_max_retries(worker, mock_repository, mock_telegram):
    """Test notification fails after max retries"""
    # Mock Telegram to fail
    mock_telegram.send_notification.side_effect = TelegramAPIError(400, "Bad Request")
    
    # Create notification at max retries
    notification = Notification.create(
        recipient_id="123456789",
        channel=NotificationChannel.TELEGRAM,
        message="Test message",
        max_retries=2
    )
    notification.retry_count = 2  # Already at max
    await mock_repository.save(notification)
    
    # Deliver notification
    await worker._deliver_notification(notification)
    
    # Verify notification status is failed
    updated = await mock_repository.get_by_id(notification.id)
    assert updated.status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_process_telegram_notification(worker, mock_repository):
    """Test processing Telegram notification message"""
    message_data = {
        'recipient_id': '123456789',
        'message': 'Hello from test',
        'metadata': {'test': True}
    }
    
    with patch.object(worker, '_deliver_notification', new_callable=AsyncMock) as mock_deliver:
        await worker._handle_telegram_notification(message_data)
        
        # Verify notification was created
        notifications = await mock_repository.get_by_recipient('123456789')
        assert len(notifications) == 1
        assert notifications[0].message == 'Hello from test'
        
        # Verify delivery was attempted
        mock_deliver.assert_called_once()


@pytest.mark.asyncio
async def test_process_reminder_notification(worker, mock_repository):
    """Test processing reminder notification"""
    message_data = {
        'reminder_id': str(uuid4()),
        'user_id': 'user123',
        'recipient_id': '123456789',
        'description': 'Buy milk'
    }
    
    with patch.object(worker, '_deliver_notification', new_callable=AsyncMock) as mock_deliver:
        await worker._handle_reminder_notification(message_data)
        
        # Verify notification was created
        notifications = await mock_repository.get_by_recipient('123456789')
        assert len(notifications) == 1
        assert 'Buy milk' in notifications[0].message
        
        # Verify delivery was attempted
        mock_deliver.assert_called_once()


@pytest.mark.asyncio
async def test_process_pending_notifications(worker, mock_repository, mock_telegram):
    """Test processing pending notifications from database"""
    # Create pending notifications
    for i in range(3):
        notification = Notification.create(
            recipient_id=f"user{i}",
            channel=NotificationChannel.TELEGRAM,
            message=f"Message {i}"
        )
        await mock_repository.save(notification)
    
    # Process pending
    processed = await worker.process_pending_notifications()
    
    # Verify all were processed
    assert processed == 3
    assert mock_telegram.send_notification.call_count == 3


@pytest.mark.asyncio
async def test_notification_retry_delay():
    """Test exponential backoff calculation"""
    notification = Notification.create(
        recipient_id="123",
        channel=NotificationChannel.TELEGRAM,
        message="Test"
    )
    
    # Test retry delay calculation
    notification.retry_count = 0
    delay_0 = notification.get_retry_delay(base_delay=1.0)
    assert delay_0 == 1.0  # 1 * 2^0
    
    notification.retry_count = 1
    delay_1 = notification.get_retry_delay(base_delay=1.0)
    assert delay_1 == 2.0  # 1 * 2^1
    
    notification.retry_count = 2
    delay_2 = notification.get_retry_delay(base_delay=1.0)
    assert delay_2 == 4.0  # 1 * 2^2
    
    notification.retry_count = 3
    delay_3 = notification.get_retry_delay(base_delay=2.0)
    assert delay_3 == 16.0  # 2 * 2^3


def test_notification_can_retry():
    """Test notification retry eligibility"""
    notification = Notification.create(
        recipient_id="123",
        channel=NotificationChannel.TELEGRAM,
        message="Test",
        max_retries=3
    )
    
    assert notification.can_retry() is True
    
    notification.retry_count = 2
    assert notification.can_retry() is True
    
    notification.retry_count = 3
    assert notification.can_retry() is False
    
    notification.mark_as_delivered()
    assert notification.can_retry() is False


def test_notification_terminal_state():
    """Test notification terminal state detection"""
    notification = Notification.create(
        recipient_id="123",
        channel=NotificationChannel.TELEGRAM,
        message="Test"
    )
    
    assert notification.is_terminal_state() is False
    
    notification.mark_as_delivered()
    assert notification.is_terminal_state() is True
    
    notification2 = Notification.create(
        recipient_id="456",
        channel=NotificationChannel.TELEGRAM,
        message="Test 2"
    )
    notification2.mark_as_failed("Error")
    assert notification2.is_terminal_state() is True


@pytest.mark.asyncio
async def test_rabbitmq_connection_failure(mock_repository, mock_telegram):
    """Test worker handles RabbitMQ connection failure"""
    mock_rabbitmq = MagicMock(spec=RabbitMQClient)
    mock_rabbitmq.ensure_connected = AsyncMock(return_value=False)
    
    worker = NotificationWorker(
        rabbitmq_client=mock_rabbitmq,
        notification_repository=mock_repository,
        telegram_client=mock_telegram
    )
    
    started = await worker.start()
    assert started is False
    assert worker.is_running is False
