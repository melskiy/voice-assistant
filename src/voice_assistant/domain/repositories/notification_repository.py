"""
Abstract interface for notification repository.

Business concept: Repository for notification delivery tracking
"""
from abc import ABC
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from ..entities.notification import Notification, NotificationStatus


class INotificationRepository(ABC):
    """Abstract interface for notification repository"""
    
    async def save(self, notification: Notification) -> None:
        """Save notification"""
        raise NotImplementedError
    
    async def get_by_id(self, notification_id: UUID) -> Optional[Notification]:
        """Get notification by ID"""
        raise NotImplementedError
    
    async def get_by_recipient(
        self, 
        recipient_id: str,
        status: Optional[NotificationStatus] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications by recipient ID with optional status filter"""
        raise NotImplementedError
    
    async def get_pending_notifications(
        self,
        limit: int = 100
    ) -> List[Notification]:
        """Get pending notifications that need to be sent"""
        raise NotImplementedError
    
    async def get_failed_notifications(
        self,
        max_retries: int = 5,
        limit: int = 100
    ) -> List[Notification]:
        """Get failed notifications that can be retried"""
        raise NotImplementedError
    
    async def update_status(
        self,
        notification_id: UUID,
        status: NotificationStatus,
        error_message: Optional[str] = None,
        external_message_id: Optional[str] = None
    ) -> None:
        """Update notification status"""
        raise NotImplementedError
    
    async def increment_retry_count(self, notification_id: UUID) -> None:
        """Increment retry count for a notification"""
        raise NotImplementedError
    
    async def delete_old_notifications(
        self,
        before_date: datetime
    ) -> int:
        """Delete old notifications, returns count deleted"""
        raise NotImplementedError
