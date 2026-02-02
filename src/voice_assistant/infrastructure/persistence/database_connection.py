import asyncio
import logging
from typing import Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration for database connection"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
        min_pool_size: int = None,
        max_pool_size: int = None,
        command_timeout: int = None,
        max_inactive_connection_lifetime: int = 300
    ):
        import os
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "5432"))
        self.database = database or os.getenv("DB_NAME", "voice_assistant")
        self.user = user or os.getenv("DB_USER", "postgres")
        self.password = password or os.getenv("DB_PASSWORD", "")
        self.min_pool_size = min_pool_size or int(os.getenv("DB_MIN_POOL_SIZE", "5"))
        self.max_pool_size = max_pool_size or int(os.getenv("DB_MAX_POOL_SIZE", "20"))
        self.command_timeout = command_timeout or int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
    
    @property
    def dsn(self) -> str:
        """Generate connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseConnectionPool:
    """
    Manages PostgreSQL connection pool using asyncpg.
    
    Implements connection pooling for optimal performance and
    proper resource management.
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[Pool] = None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the connection pool"""
        async with self._lock:
            if self._initialized:
                return
            
            try:
                self._pool = await asyncpg.create_pool(
                    dsn=self.config.dsn,
                    min_size=self.config.min_pool_size,
                    max_size=self.config.max_pool_size,
                    command_timeout=self.config.command_timeout,
                    max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                    init=self._init_connection
                )
                self._initialized = True
                logger.info(f"Database pool initialized with {self.config.min_pool_size}-{self.config.max_pool_size} connections")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise
    
    async def _init_connection(self, conn: Connection) -> None:
        """Initialize new connection with custom settings"""
        # Enable UUID extension
        await conn.set_type_codec(
            'uuid',
            encoder=lambda x: str(x),
            decoder=lambda x: x,
            schema='pg_catalog'
        )
    
    async def close(self) -> None:
        """Close the connection pool"""
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._initialized = False
                logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[Connection, None]:
        """Acquire a connection from the pool"""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Connection, None]:
        """Acquire a connection with transaction"""
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """Fetch multiple rows"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    @property
    def is_initialized(self) -> bool:
        """Check if pool is initialized"""
        return self._initialized


class UnitOfWork:
    """
    Unit of Work pattern for transactional operations.
    
    Manages transactions across multiple repositories ensuring
    atomic operations for complex data modifications.
    """
    
    def __init__(self, db_pool: DatabaseConnectionPool):
        self._db_pool = db_pool
        self._connection: Optional[Connection] = None
        self._transaction = None
        self._is_committed = False
    
    async def __aenter__(self):
        """Enter context manager and start transaction"""
        self._connection = await self._db_pool._pool.acquire()
        self._transaction = self._connection.transaction()
        await self._transaction.start()
        logger.debug("Unit of work started")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and handle transaction"""
        try:
            if exc_type is not None:
                # Exception occurred, rollback
                await self._transaction.rollback()
                logger.warning(f"Unit of work rolled back due to: {exc_val}")
            elif not self._is_committed:
                # No commit called, rollback
                await self._transaction.rollback()
                logger.debug("Unit of work rolled back (no commit)")
            # If committed, transaction is already finalized
        finally:
            await self._db_pool._pool.release(self._connection)
            self._connection = None
            self._transaction = None
    
    async def commit(self) -> None:
        """Commit the transaction"""
        if self._transaction:
            await self._transaction.commit()
            self._is_committed = True
            logger.debug("Unit of work committed")
    
    async def rollback(self) -> None:
        """Rollback the transaction"""
        if self._transaction:
            await self._transaction.rollback()
            logger.debug("Unit of work rolled back")
    
    @property
    def connection(self) -> Connection:
        """Get the current connection"""
        if not self._connection:
            raise RuntimeError("Unit of work not started")
        return self._connection
