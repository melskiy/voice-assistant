"""
Redis Storage Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    IStorageService
)
from ..interfaces import IRedisClient, ICacheSerializer
from .services.redis_client import RedisClientFactory, JsonCacheSerializer
from .services.storage_service import RedisStorageService


class RedisStoragePluginRegistration(IPluginRegistration):
    """
    Registration class for Redis storage plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="storage.redis",
            name="Redis Storage",
            version="1.0.0",
            description="Redis caching and session storage",
            author="Voice Assistant Team",
            dependencies=["redis"]
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            JSON Schema for configuration validation
        """
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "default": "redis://localhost:6379",
                    "description": "Redis connection URL"
                },
                "host": {
                    "type": "string",
                    "default": "localhost",
                    "description": "Redis host"
                },
                "port": {
                    "type": "integer",
                    "default": 6379,
                    "description": "Redis port"
                },
                "db": {
                    "type": "integer",
                    "default": 0,
                    "description": "Redis database number"
                },
                "password": {
                    "type": "string",
                    "default": "",
                    "description": "Redis password"
                },
                "default_ttl": {
                    "type": "integer",
                    "default": 1800,
                    "description": "Default TTL in seconds"
                },
                "max_connections": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum connection pool size"
                }
            },
            "required": []
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if redis is available.
        
        Returns:
            True if redis is installed
        """
        try:
            import redis
            return True
        except ImportError:
            return False
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register Redis storage dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Extract configuration
        default_ttl = config.get("default_ttl", 1800)
        
        # Register configuration as named instance
        container.add_instance(config, name="storage_redis_config")
        
        # Register Redis client as singleton
        def client_factory(c: Container) -> IRedisClient:
            return RedisClientFactory.create(config)
        
        container.add_singleton(IRedisClient, client_factory)
        
        # Register serializer as singleton
        def serializer_factory(c: Container) -> ICacheSerializer:
            return JsonCacheSerializer()
        
        container.add_singleton(ICacheSerializer, serializer_factory)
        
        # Register storage service as singleton
        def service_factory(c: Container) -> IStorageService:
            client = c.resolve(IRedisClient)
            serializer = c.resolve(ICacheSerializer)
            return RedisStorageService(
                redis_client=client,
                serializer=serializer,
                default_ttl=default_ttl
            )
        
        container.add_singleton(IStorageService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
