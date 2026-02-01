"""
PostgreSQL Storage Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    IStorageService
)
from ..interfaces import IConnectionPool
from .services.connection_pool import ConnectionPoolFactory
from .services.storage_service import PostgresStorageService


class PostgresStoragePluginRegistration(IPluginRegistration):
    """
    Registration class for PostgreSQL storage plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="storage.postgres",
            name="PostgreSQL Storage",
            version="1.0.0",
            description="PostgreSQL database storage",
            author="Voice Assistant Team",
            dependencies=["asyncpg"]
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
                "connection_string": {
                    "type": "string",
                    "description": "PostgreSQL connection string"
                },
                "host": {
                    "type": "string",
                    "default": "localhost",
                    "description": "Database host"
                },
                "port": {
                    "type": "integer",
                    "default": 5432,
                    "description": "Database port"
                },
                "database": {
                    "type": "string",
                    "default": "voice_assistant",
                    "description": "Database name"
                },
                "username": {
                    "type": "string",
                    "default": "postgres",
                    "description": "Database username"
                },
                "password": {
                    "type": "string",
                    "default": "",
                    "description": "Database password"
                },
                "pool_min_size": {
                    "type": "integer",
                    "default": 5,
                    "description": "Minimum connection pool size"
                },
                "pool_max_size": {
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
        Check if asyncpg is available.
        
        Returns:
            True if asyncpg is installed
        """
        try:
            import asyncpg
            return True
        except ImportError:
            return False
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register PostgreSQL storage dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Register configuration as named instance
        container.add_instance(config, name="storage_postgres_config")
        
        # Register connection pool as singleton with lazy initialization
        async def pool_factory():
            pool = ConnectionPoolFactory.create(config)
            await pool.initialize()
            return pool
        
        container.add_singleton(IConnectionPool, pool_factory)
        
        # Register storage service as singleton
        def service_factory(c: Container) -> IStorageService:
            pool = c.resolve(IConnectionPool)
            return PostgresStorageService(connection_pool=pool)
        
        container.add_singleton(IStorageService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
