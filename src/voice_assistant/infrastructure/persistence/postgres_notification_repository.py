"""
PostgreSQL implementation of notification repository.

Business concept: Persistence layer for notification tracking
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import json

from ...domain.entities.notification import Notification, NotificationStatus, NotificationChannel
from ...domain.repositories.notification_repository import INotificationRepository
from .database_connection import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class PostgresNotificationRepository(INotificationRepository):
    """
    PostgreSQL implementation of notification repository.
    
    Stores notification delivery status and tracks retry attempts.
    """
    
    def __init__(self, db_pool: DatabaseConnectionPool):
        self._db_pool = db_pool
    
    async def _ensure_table_exists(self) -> None:
        """Ensure notifications table exists"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY,
            recipient_id VARCHAR(255) NOT NULL,
            channel VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            sent_at TIMESTAMP WITH TIME ZONE,
            delivered_at TIMESTAMP WITH TIME ZONE,
            failed_at TIMESTAMP WITH TIME ZONE,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 5,
            error_message TEXT,
            metadata JSONB DEFAULT '{}',
            external_message_id VARCHAR(255)
        );
        
        CREATE INDEX IF NOT EXISTS idx_notifications_recipient 
            ON notifications(recipient_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_status 
            ON notifications(status);
        CREATE INDEX IF NOT EXISTS idx_notifications_created_at 
            ON notifications(created_at);
        """
        
        try:
            await self._db_pool.execute(create_table_sql)
        except Exception as e:
            # Table might already exist
            logger.debug(f"Table creation (may already exist): {e}")
    
    def _row_to_notification(self, row) -> Notification:
        """Convert database row to Notification entity"""
        return Notification(
            id=row['id'],
            recipient_id=row['recipient_id'],
            channel=NotificationChannel(row['channel']),
            message=row['message'],
            status=NotificationStatus(row['status']),
            created_at=row['created_at'],
            sent_at=row['sent_at'],
            delivered_at=row['delivered_at'],
            failed_at=row['failed_at'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
            error_message=row['error_message'],
            metadata=row['metadata'] if isinstance(row['metadata'], dict) else json.loads(row['metadata'] or '{}'),
            external_message_id=row['external_message_id']
        )
    
    async def save(self, notification: Notification) -> None:
        """Save notification"""
        await self._ensure_table_exists()
        
        sql = """
        INSERT INTO notifications (
            id, recipient_id, channel, message, status, created_at,
            sent_at, delivered_at, failed_at, retry_count, max_retries,
            error_message, metadata, external_message_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            sent_at = EXCLUDED.sent_at,
            delivered_at = EXCLUDED.delivered_at,
            failed_at = EXCLUDED.failed_at,
            retry_count = EXCLUDED.retry_count,
            error_message = EXCLUDED.error_message,
            external_message_id = EXCLUDED.external_message_id
        """
        
        await self._db_pool.execute(
            sql,
            notification.id,
            notification.recipient_id,
            notification.channel.value,
            notification.message,
            notification.status.value,
            notification.created_at,
            notification.sent_at,
            notification.delivered_at,
            notification.failed_at,
            notification.retry_count,
            notification.max_retries,
            notification.error_message,
            json.dumps(notification.metadata),
            notification.external_message_id
        )
        
        logger.debug(f"Saved notification {notification.id}")
    
    async def get_by_id(self, notification_id: UUID) -> Optional[Notification]:
        """Get notification by ID"""
        await self._ensure_table_exists()
        
        sql = "SELECT * FROM notifications WHERE id = $1"
        row = await self._db_pool.fetchrow(sql, notification_id)
        
        if row:
            return self._row_to_notification(row)
        return None
    
    async def get_by_recipient(
        self, 
        recipient_id: str,
        status: Optional[NotificationStatus] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications by recipient ID with optional status filter"""
        await self._ensure_table_exists()
        
        if status:
            sql = """
            SELECT * FROM notifications 
            WHERE recipient_id = $1 AND status = $2
            ORDER BY created_at DESC
            LIMIT $3
            """
            rows = await self._db_pool.fetch(sql, recipient_id, status.value, limit)
        else:
            sql = """
            SELECT * FROM notifications 
            WHERE recipient_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """
            rows = await self._db_pool.fetch(sql, recipient_id, limit)
        
        return [self._row_to_notification(row) for row in rows]
    
    async def get_pending_notifications(
        self,
        limit: int = 100
    ) -> List[Notification]:
        """Get pending notifications that need to be sent"""
        await self._ensure_table_exists()
        
        sql = """
        SELECT * FROM notifications 
        WHERE status IN ('pending', 'retrying')
        ORDER BY created_at ASC
        LIMIT $1
        """
        
        rows = await self._db_pool.fetch(sql, limit)
        return [self._row_to_notification(row) for row in rows]
    
    async def get_failed_notifications(
        self,
        max_retries: int = 5,
        limit: int = 100
    ) -> List[Notification]:
        """Get failed notifications that can be retried"""
        await self._ensure_table_exists()
        
        sql = """
        SELECT * FROM notifications 
        WHERE status = 'failed' AND retry_count < $1
        ORDER BY created_at ASC
        LIMIT $2
        """
        
        rows = await self._db_pool.fetch(sql, max_retries, limit)
        return [self._row_to_notification(row) for row in rows]
    
    async def update_status(
        self,
        notification_id: UUID,
        status: NotificationStatus,
        error_message: Optional[str] = None,
        external_message_id: Optional[str] = None
    ) -> None:
        """Update notification status"""
        await self._ensure_table_exists()
        
        # Determine timestamp field based on status
        timestamp_field = None
        timestamp_value = datetime.utcnow()
        
        if status == NotificationStatus.SENT:
            timestamp_field = "sent_at"
        elif status == NotificationStatus.DELIVERED:
            timestamp_field = "delivered_at"
        elif status == NotificationStatus.FAILED:
            timestamp_field = "failed_at"
        
        if timestamp_field:
            sql = f"""
            UPDATE notifications 
            SET status = $1, {timestamp_field} = $2, error_message = $3, external_message_id = $4
            WHERE id = $5
            """
            await self._db_pool.execute(
                sql, status.value, timestamp_value, error_message, 
                external_message_id, notification_id
            )
        else:
            sql = """
            UPDATE notifications 
            SET status = $1, error_message = $2, external_message_id = $3
            WHERE id = $4
            """
            await self._db_pool.execute(
                sql, status.value, error_message, external_message_id, notification_id
            )
        
        logger.debug(f"Updated notification {notification_id} status to {status.value}")
    
    async def increment_retry_count(self, notification_id: UUID) -> None:
        """Increment retry count for a notification"""
        await self._ensure_table_exists()
        
        sql = """
        UPDATE notifications 
        SET retry_count = retry_count + 1
        WHERE id = $1
        """
        
        await self._db_pool.execute(sql, notification_id)
        logger.debug(f"Incremented retry count for notification {notification_id}")
    
    async def delete_old_notifications(
        self,
        before_date: datetime
    ) -> int:
        """Delete old notifications, returns count deleted"""
        await self._ensure_table_exists()
        
        sql = """
        DELETE FROM notifications 
        WHERE created_at < $1
        RETURNING id
        """
        
        rows = await self._db_pool.fetch(sql, before_date)
        deleted_count = len(rows)
        logger.info(f"Deleted {deleted_count} old notifications")
        return deleted_count
