"""
Redis Storage Plugin.

This plugin provides Redis caching and session storage.

Usage:
    from rodi import Container
    from plugins.storage_redis import RedisStoragePluginRegistration
    
    container = Container()
    config = {"url": "redis://localhost:6379", "default_ttl": 1800}
    RedisStoragePluginRegistration.register(container, config)
    
    # Resolve and use the service
    storage_service = container.resolve(IStorageService)
    await storage_service.set("key", {"data": "value"})
"""

from .registration import RedisStoragePluginRegistration
from .interfaces import IRedisClient, ICacheSerializer
from .services.redis_client import RedisClient, JsonCacheSerializer, RedisClientFactory
from .services.storage_service import RedisStorageService

__all__ = [
    # Registration
    "RedisStoragePluginRegistration",
    # Interfaces
    "IRedisClient",
    "ICacheSerializer",
    # Services
    "RedisClient",
    "JsonCacheSerializer",
    "RedisClientFactory",
    "RedisStorageService",
]
