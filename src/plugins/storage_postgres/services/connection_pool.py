"""
PostgreSQL connection pool implementation.
"""

from typing import Optional

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

from ..interfaces import IConnectionPool, IDatabaseConnection


class AsyncpgConnectionPool(IConnectionPool):
    """
    PostgreSQL connection pool using asyncpg.
    """
    
    def __init__(
        self,
        connection_string: str,
        min_size: int = 5,
        max_size: int = 20
    ):
        """
        Initialize connection pool.
        
        Args:
            connection_string: PostgreSQL connection string
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        if not ASYNCPG_AVAILABLE:
            raise RuntimeError("asyncpg is not installed")
        
        self._connection_string = connection_string
        self._min_size = min_size
        self._max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        self._pool = await asyncpg.create_pool(
            self._connection_string,
            min_size=self._min_size,
            max_size=self._max_size
        )
    
    async def acquire(self) -> 'AsyncpgConnection':
        """Acquire a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        
        conn = await self._pool.acquire()
        return AsyncpgConnection(conn)
    
    async def release(self, connection: 'AsyncpgConnection') -> None:
        """Release a connection back to the pool."""
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        
        await self._pool.release(connection._conn)
    
    async def close(self) -> None:
        """Close the pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


class AsyncpgConnection(IDatabaseConnection):
    """
    Wrapper for asyncpg connection.
    """
    
    def __init__(self, conn: asyncpg.Connection):
        """
        Initialize connection wrapper.
        
        Args:
            conn: asyncpg connection
        """
        self._conn = conn
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query."""
        return await self._conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch results from a query."""
        return await self._conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """Fetch a single row."""
        row = await self._conn.fetchrow(query, *args)
        return dict(row) if row else None


class ConnectionPoolFactory:
    """
    Factory for creating connection pools.
    """
    
    @staticmethod
    def create(config: dict) -> AsyncpgConnectionPool:
        """
        Create a connection pool from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configured connection pool
        """
        connection_string = config.get("connection_string")
        if not connection_string:
            # Build connection string from components
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            database = config.get("database", "voice_assistant")
            user = config.get("username", "postgres")
            password = config.get("password", "")
            
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        min_size = config.get("pool_min_size", 5)
        max_size = config.get("pool_max_size", 20)
        
        return AsyncpgConnectionPool(
            connection_string=connection_string,
            min_size=min_size,
            max_size=max_size
        )
