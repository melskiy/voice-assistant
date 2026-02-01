"""
PostgreSQL storage service implementation.
"""

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseStorageService,
)
from ..interfaces import IConnectionPool


class PostgresStorageService(BaseStorageService):
    """
    PostgreSQL storage service.
    
    Provides database connectivity through connection pool.
    """
    
    def __init__(self, connection_pool: IConnectionPool):
        """
        Initialize storage service.
        
        Args:
            connection_pool: Database connection pool
        """
        self._pool = connection_pool
    
    async def initialize(self) -> None:
        """Initialize the service (initialize connection pool)."""
        if hasattr(self._pool, 'initialize'):
            await self._pool.initialize()
    
    async def shutdown(self) -> None:
        """Cleanup resources (close connection pool)."""
        await self._pool.close()
    
    async def connect(self) -> None:
        """Establish connection to storage."""
        # Pool is already connected during initialization
        pass
    
    async def disconnect(self) -> None:
        """Close connection to storage."""
        await self._pool.close()
    
    async def health_check(self) -> bool:
        """Check if storage is accessible."""
        try:
            conn = await self._pool.acquire()
            try:
                await conn.execute("SELECT 1")
                return True
            finally:
                await self._pool.release(conn)
        except Exception:
            return False
    
    async def acquire_connection(self):
        """Acquire a connection from the pool."""
        return await self._pool.acquire()
    
    async def release_connection(self, conn):
        """Release a connection back to the pool."""
        await self._pool.release(conn)
