"""
Interfaces for RabbitMQ messaging plugin.
"""

from typing import Protocol, runtime_checkable, Callable, Optional, Any


@runtime_checkable
class IRabbitMQConnection(Protocol):
    """Interface for RabbitMQ connection."""
    
    async def connect(self) -> None:
        """Establish connection."""
        ...
    
    async def close(self) -> None:
        """Close connection."""
        ...
    
    async def channel(self) -> 'IRabbitMQChannel':
        """Get a channel."""
        ...


@runtime_checkable
class IRabbitMQChannel(Protocol):
    """Interface for RabbitMQ channel."""
    
    async def declare_exchange(
        self,
        name: str,
        exchange_type: str
    ) -> 'IRabbitMQExchange':
        """Declare an exchange."""
        ...
    
    async def declare_queue(self, name: str) -> 'IRabbitMQQueue':
        """Declare a queue."""
        ...
    
    async def close(self) -> None:
        """Close channel."""
        ...


@runtime_checkable
class IRabbitMQExchange(Protocol):
    """Interface for RabbitMQ exchange."""
    
    async def publish(
        self,
        message: bytes,
        routing_key: str
    ) -> None:
        """Publish a message."""
        ...


@runtime_checkable
class IRabbitMQQueue(Protocol):
    """Interface for RabbitMQ queue."""
    
    async def bind(
        self,
        exchange: IRabbitMQExchange,
        routing_key: str
    ) -> None:
        """Bind queue to exchange."""
        ...
    
    async def consume(
        self,
        callback: Callable[[bytes], Any]
    ) -> None:
        """Start consuming messages."""
        ...
