"""
Domain entity for notification delivery tracking.

Business concept: Tracks the lifecycle of notification delivery attempts
including status, retry attempts, and delivery confirmation.
Constraints: Delivery status must be one of PENDING, SENT, DELIVERED, FAILED
"""
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationChannel(str, Enum):
    """Supported notification channels"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class Notification(BaseModel):
    """
    Domain entity representing a notification delivery attempt.
    
    Business rules:
    - Max retry attempts: 5
    - Retry delay follows exponential backoff: 2^attempt * base_delay
    - Failed notifications are archived after max retries
    """
    id: UUID = Field(default_factory=uuid4)
    recipient_id: str
    channel: NotificationChannel
    message: str
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 5
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    external_message_id: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def can_retry(self) -> bool:
        """Check if notification can be retried"""
        return self.retry_count < self.max_retries and self.status != NotificationStatus.DELIVERED
    
    def mark_as_sent(self, external_message_id: Optional[str] = None) -> None:
        """Mark notification as sent"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
        if external_message_id:
            self.external_message_id = external_message_id
    
    def mark_as_delivered(self) -> None:
        """Mark notification as delivered"""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """Mark notification as failed"""
        self.status = NotificationStatus.FAILED
        self.failed_at = datetime.utcnow()
        self.error_message = error_message
    
    def increment_retry(self) -> None:
        """Increment retry counter and update status"""
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            self.status = NotificationStatus.RETRYING
        else:
            self.status = NotificationStatus.FAILED
    
    def get_retry_delay(self, base_delay: float = 1.0) -> float:
        """
        Calculate retry delay using exponential backoff.
        Formula: base_delay * (2 ^ retry_count)
        """
        return base_delay * (2 ** self.retry_count)
    
    def is_terminal_state(self) -> bool:
        """Check if notification is in terminal state"""
        return self.status in (NotificationStatus.DELIVERED, NotificationStatus.FAILED)
    
    @classmethod
    def create(
        cls,
        recipient_id: str,
        channel: NotificationChannel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        max_retries: int = 5
    ) -> 'Notification':
        """Factory method to create a notification"""
        return cls(
            recipient_id=recipient_id,
            channel=channel,
            message=message,
            metadata=metadata or {},
            max_retries=max_retries
        )
    
    def __str__(self) -> str:
        return f"Notification({self.id}): {self.channel.value} to {self.recipient_id} - {self.status.value}"
