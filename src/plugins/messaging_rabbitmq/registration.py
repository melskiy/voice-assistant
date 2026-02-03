"""
RabbitMQ Messaging Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    IMessagingService
)
from ..interfaces import IRabbitMQConnection
from .services.rabbitmq_connection import RabbitMQConnectionFactory
from .services.messaging_service import RabbitMQMessagingService


class RabbitMQMessagingPluginRegistration(IPluginRegistration):
    """
    Registration class for RabbitMQ messaging plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="messaging.rabbitmq",
            name="RabbitMQ Messaging",
            version="1.0.0",
            description="RabbitMQ message broker integration",
            author="Voice Assistant Team",
            dependencies=["aio-pika"]
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
                    "default": "amqp://guest:guest@localhost:5672/",
                    "description": "RabbitMQ connection URL"
                },
                "host": {
                    "type": "string",
                    "default": "localhost",
                    "description": "RabbitMQ host"
                },
                "port": {
                    "type": "integer",
                    "default": 5672,
                    "description": "RabbitMQ port"
                },
                "username": {
                    "type": "string",
                    "default": "guest",
                    "description": "RabbitMQ username"
                },
                "password": {
                    "type": "string",
                    "default": "guest",
                    "description": "RabbitMQ password"
                },
                "virtual_host": {
                    "type": "string",
                    "default": "/",
                    "description": "RabbitMQ virtual host"
                },
                "exchange_name": {
                    "type": "string",
                    "default": "voice_assistant_exchange",
                    "description": "Exchange name"
                },
                "exchange_type": {
                    "type": "string",
                    "default": "topic",
                    "enum": ["direct", "topic", "fanout", "headers"],
                    "description": "Exchange type"
                }
            },
            "required": []
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if aio-pika is available.
        
        Returns:
            True if aio-pika is installed
        """
        try:
            import aio_pika
            return True
        except ImportError:
            return False
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register RabbitMQ messaging dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Extract configuration
        exchange_name = config.get("exchange_name", "voice_assistant_exchange")
        exchange_type = config.get("exchange_type", "topic")
        
        # Register configuration as named instance
        container.add_instance(config, name="messaging_rabbitmq_config")
        
        # Register connection as singleton
        def connection_factory(c: Container) -> IRabbitMQConnection:
            return RabbitMQConnectionFactory.create(config)
        
        container.add_singleton(IRabbitMQConnection, connection_factory)
        
        # Register messaging service as singleton
        async def service_factory(c: Container) -> IMessagingService:
            connection = c.resolve(IRabbitMQConnection)
            service = RabbitMQMessagingService(
                connection=connection,
                exchange_name=exchange_name,
                exchange_type=exchange_type
            )
            await service.initialize()
            return service
        
        container.add_singleton(IMessagingService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
