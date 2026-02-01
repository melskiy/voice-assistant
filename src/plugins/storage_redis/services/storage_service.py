"""
Redis storage service implementation.
"""

from typing import Optional, Any

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseStorageService,
)
from ..interfaces import IRedisClient, ICacheSerializer


class RedisStorageService(BaseStorageService):
    """
    Redis storage service.
    
    Provides caching and session storage capabilities.
    """
    
    def __init__(
        self,
        redis_client: IRedisClient,
        serializer: ICacheSerializer,
        default_ttl: int = 1800
    ):
        """
        Initialize storage service.
        
        Args:
            redis_client: Redis client
            serializer: Data serializer
            default_ttl: Default TTL in seconds
        """
        self._client = redis_client
        self._serializer = serializer
        self._default_ttl = default_ttl
    
    async def initialize(self) -> None:
        """Initialize the service."""
        # Client is already connected
        pass
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        if hasattr(self._client, 'close'):
            await self._client.close()
    
    async def connect(self) -> None:
        """Establish connection to storage."""
        pass
    
    async def disconnect(self) -> None:
        """Close connection to storage."""
        await self.shutdown()
    
    async def health_check(self) -> bool:
        """Check if storage is accessible."""
        try:
            await self._client.exists("health_check")
            return True
        except Exception:
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None
        """
        data = await self._client.get(key)
        if data:
            return self._serializer.deserialize(data)
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL (uses default if not specified)
            
        Returns:
            True if successful
        """
        data = self._serializer.serialize(value)
        return await self._client.set(key, data, ttl or self._default_ttl)
    
    async def delete(self, key: str) -> bool:
        """
        Delete cached value.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        return await self._client.delete(key)
