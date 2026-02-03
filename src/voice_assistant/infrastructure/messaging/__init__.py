"""
Messaging infrastructure module.

Provides RabbitMQ client for async messaging.
"""
from .rabbitmq_client import RabbitMQClient, RabbitMQConfig

__all__ = ['RabbitMQClient', 'RabbitMQConfig']
