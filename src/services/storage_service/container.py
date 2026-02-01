"""
Dependency Injection Container for Storage Service.
Configures repositories and database connections using DDD principles.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""
import os
import logging
from typing import Optional

from rodi import Container

from ...voice_assistant.domain.repositories.shopping_repository import IShoppingRepository
from ...voice_assistant.domain.repositories.reminder_repository import IReminderRepository
from ...voice_assistant.infrastructure.persistence.database_connection import (
    DatabaseConnectionPool, DatabaseConfig
)
from ...voice_assistant.infrastructure.persistence.postgres_shopping_repository import (
    PostgresShoppingRepository
)
from ...voice_assistant.infrastructure.persistence.postgres_reminder_repository import (
    PostgresReminderRepository
)

logger = logging.getLogger(__name__)


class StorageServiceContainer:
    """
    IoC Container for Storage Service.
    
    Manages dependency injection for:
    - Database connection pool
    - Repository implementations
    - Unit of Work
    """
    
    def __init__(self):
        self._container = Container()
        self._is_configured = False
        self._db_pool: Optional[DatabaseConnectionPool] = None
    
    def configure(self, config: Optional[DatabaseConfig] = None) -> None:
        """Configure the container with dependencies"""
        if self._is_configured:
            return
        
        # Create database config from environment or use provided config
        if config is None:
            config = self._create_config_from_env()
        
        # Register database connection pool as singleton
        self._db_pool = DatabaseConnectionPool(config)
        self._container.add_singleton(
            DatabaseConnectionPool,
            lambda: self._db_pool
        )
        
        # Register repositories
        self._container.add_singleton(
            IShoppingRepository,
            lambda: PostgresShoppingRepository(self._db_pool)
        )
        
        self._container.add_singleton(
            IReminderRepository,
            lambda: PostgresReminderRepository(self._db_pool)
        )
        
        self._is_configured = True
        logger.info("Storage service container configured")
    
    def _create_config_from_env(self) -> DatabaseConfig:
        """Create database config from environment variables"""
        return DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'voice_assistant'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            min_pool_size=int(os.getenv('DB_MIN_POOL_SIZE', '5')),
            max_pool_size=int(os.getenv('DB_MAX_POOL_SIZE', '20')),
            command_timeout=int(os.getenv('DB_COMMAND_TIMEOUT', '60'))
        )
    
    def get_shopping_repository(self) -> IShoppingRepository:
        """Get shopping repository instance"""
        if not self._is_configured:
            self.configure()
        return self._container.resolve(IShoppingRepository)
    
    def get_reminder_repository(self) -> IReminderRepository:
        """Get reminder repository instance"""
        if not self._is_configured:
            self.configure()
        return self._container.resolve(IReminderRepository)
    
    def get_db_pool(self) -> DatabaseConnectionPool:
        """Get database connection pool"""
        if not self._is_configured:
            self.configure()
        return self._container.resolve(DatabaseConnectionPool)
    
    async def initialize(self) -> None:
        """Initialize database connections"""
        if not self._is_configured:
            self.configure()
        
        if self._db_pool:
            await self._db_pool.initialize()
            logger.info("Storage service database initialized")
    
    async def shutdown(self) -> None:
        """Shutdown database connections"""
        if self._db_pool:
            await self._db_pool.close()
            logger.info("Storage service database shutdown")


# Global container instance
_container_instance: Optional[StorageServiceContainer] = None


def get_container() -> StorageServiceContainer:
    """Get or create the global container instance"""
    global _container_instance
    if _container_instance is None:
        _container_instance = StorageServiceContainer()
    return _container_instance
