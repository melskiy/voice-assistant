"""
PostgreSQL Storage Plugin.

This plugin provides PostgreSQL database storage.

Usage:
    from rodi import Container
    from plugins.storage_postgres import PostgresStoragePluginRegistration
    
    container = Container()
    config = {"connection_string": "postgresql://user:pass@localhost/db"}
    PostgresStoragePluginRegistration.register(container, config)
    
    # Resolve and use the service
    storage_service = container.resolve(IStorageService)
    await storage_service.initialize()
"""

from .registration import PostgresStoragePluginRegistration
from .interfaces import IDatabaseConnection, IConnectionPool, ITransaction
from .services.connection_pool import (
    AsyncpgConnectionPool,
    AsyncpgConnection,
    ConnectionPoolFactory
)
from .services.storage_service import PostgresStorageService

__all__ = [
    # Registration
    "PostgresStoragePluginRegistration",
    # Interfaces
    "IDatabaseConnection",
    "IConnectionPool",
    "ITransaction",
    # Services
    "AsyncpgConnectionPool",
    "AsyncpgConnection",
    "ConnectionPoolFactory",
    "PostgresStorageService",
]
