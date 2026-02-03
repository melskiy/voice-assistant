"""
RabbitMQ Messaging Plugin.

This plugin provides RabbitMQ message broker integration.

Usage:
    from rodi import Container
    from plugins.messaging_rabbitmq import RabbitMQMessagingPluginRegistration
    
    container = Container()
    config = {"url": "amqp://guest:guest@localhost:5672/"}
    RabbitMQMessagingPluginRegistration.register(container, config)
    
    # Resolve and use the service
    messaging_service = container.resolve(IMessagingService)
    await messaging_service.publish("routing.key", b"message")
"""

from .registration import RabbitMQMessagingPluginRegistration
from .interfaces import (
    IRabbitMQConnection,
    IRabbitMQChannel,
    IRabbitMQExchange,
    IRabbitMQQueue
)
from .services.rabbitmq_connection import (
    AioPikaConnection,
    AioPikaChannel,
    AioPikaExchange,
    AioPikaQueue,
    RabbitMQConnectionFactory
)
from .services.messaging_service import RabbitMQMessagingService

__all__ = [
    # Registration
    "RabbitMQMessagingPluginRegistration",
    # Interfaces
    "IRabbitMQConnection",
    "IRabbitMQChannel",
    "IRabbitMQExchange",
    "IRabbitMQQueue",
    # Services
    "AioPikaConnection",
    "AioPikaChannel",
    "AioPikaExchange",
    "AioPikaQueue",
    "RabbitMQConnectionFactory",
    "RabbitMQMessagingService",
]
