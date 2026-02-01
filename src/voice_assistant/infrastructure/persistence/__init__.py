"""
Persistence infrastructure module.

Provides database connection management and repository implementations.
"""
from .database_connection import DatabaseConnectionPool, DatabaseConfig, UnitOfWork
from .postgres_reminder_repository import PostgresReminderRepository
from .postgres_shopping_repository import PostgresShoppingRepository
from .postgres_notification_repository import PostgresNotificationRepository

__all__ = [
    'DatabaseConnectionPool',
    'DatabaseConfig',
    'UnitOfWork',
    'PostgresReminderRepository',
    'PostgresShoppingRepository',
    'PostgresNotificationRepository'
]
