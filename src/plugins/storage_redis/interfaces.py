"""
Interfaces for Redis storage plugin.
"""

from typing import Protocol, runtime_checkable, Any, Optional


@runtime_checkable
class IRedisClient(Protocol):
    """Interface for Redis client."""
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        ...
    
    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        ...


@runtime_checkable
class ICacheSerializer(Protocol):
    """Interface for cache data serializer."""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
        ...
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to data."""
        ...
