"""
Interfaces for PostgreSQL storage plugin.
"""

from typing import Protocol, runtime_checkable, Any, Optional
from contextlib import asynccontextmanager


@runtime_checkable
class IDatabaseConnection(Protocol):
    """Interface for database connection."""
    
    async def execute(self, query: str, *args) -> Any:
        """Execute a query."""
        ...
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch results from a query."""
        ...
    
    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """Fetch a single row."""
        ...


@runtime_checkable
class IConnectionPool(Protocol):
    """Interface for database connection pool."""
    
    async def acquire(self) -> IDatabaseConnection:
        """Acquire a connection from the pool."""
        ...
    
    async def release(self, connection: IDatabaseConnection) -> None:
        """Release a connection back to the pool."""
        ...
    
    async def close(self) -> None:
        """Close the pool."""
        ...


@runtime_checkable
class ITransaction(Protocol):
    """Interface for database transaction."""
    
    async def commit(self) -> None:
        """Commit the transaction."""
        ...
    
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...
