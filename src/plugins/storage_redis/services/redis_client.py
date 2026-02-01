"""
Redis client implementation.
"""

import json
from typing import Optional, Any

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..interfaces import IRedisClient, ICacheSerializer


class RedisClient(IRedisClient):
    """
    Async Redis client wrapper.
    """
    
    def __init__(self, client: redis.Redis):
        """
        Initialize Redis client.
        
        Args:
            client: Redis client instance
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis is not installed")
        
        self._client = client
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        return await self._client.get(key)
    
    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value with optional TTL."""
        return await self._client.set(key, value, ex=ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        result = await self._client.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        result = await self._client.exists(key)
        return result > 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        return await self._client.expire(key, seconds)
    
    async def close(self) -> None:
        """Close the connection."""
        await self._client.close()


class JsonCacheSerializer(ICacheSerializer):
    """
    JSON-based cache serializer.
    """
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        return json.dumps(data).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to data."""
        return json.loads(data.decode('utf-8'))


class RedisClientFactory:
    """
    Factory for creating Redis clients.
    """
    
    @staticmethod
    def create(config: dict) -> RedisClient:
        """
        Create a Redis client from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configured Redis client
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis is not installed")
        
        url = config.get("url")
        
        if url:
            client = redis.from_url(
                url,
                decode_responses=False,
                max_connections=config.get("max_connections", 20)
            )
        else:
            client = redis.Redis(
                host=config.get("host", "localhost"),
                port=config.get("port", 6379),
                db=config.get("db", 0),
                password=config.get("password") or None,
                decode_responses=False,
                max_connections=config.get("max_connections", 20)
            )
        
        return RedisClient(client)
