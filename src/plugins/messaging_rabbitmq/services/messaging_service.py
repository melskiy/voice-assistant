"""
RabbitMQ messaging service implementation.
"""

from typing import Callable, Optional, Any, Dict

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    BaseMessagingService,
)
from ..interfaces import (
    IRabbitMQConnection,
    IRabbitMQExchange,
    IRabbitMQChannel
)


class RabbitMQMessagingService(BaseMessagingService):
    """
    RabbitMQ messaging service.
    
    Provides publish/subscribe messaging capabilities.
    """
    
    def __init__(
        self,
        connection: IRabbitMQConnection,
        exchange_name: str = "voice_assistant_exchange",
        exchange_type: str = "topic"
    ):
        """
        Initialize messaging service.
        
        Args:
            connection: RabbitMQ connection
            exchange_name: Exchange name
            exchange_type: Exchange type (direct, topic, fanout, headers)
        """
        self._connection = connection
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._exchange: Optional[IRabbitMQExchange] = None
        self._channel: Optional[IRabbitMQChannel] = None
        self._consumers: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize the service."""
        await self._connection.connect()
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._channel:
            await self._channel.close()
        await self._connection.close()
    
    async def connect(self) -> None:
        """Establish connection to messaging broker."""
        await self._connection.connect()
    
    async def disconnect(self) -> None:
        """Close connection to messaging broker."""
        await self.shutdown()
    
    async def _ensure_channel(self) -> IRabbitMQChannel:
        """Ensure channel is created."""
        if not self._channel:
            self._channel = await self._connection.channel()
        return self._channel
    
    async def _ensure_exchange(self) -> IRabbitMQExchange:
        """Ensure exchange is declared."""
        if not self._exchange:
            channel = await self._ensure_channel()
            self._exchange = await channel.declare_exchange(
                self._exchange_name,
                self._exchange_type
            )
        return self._exchange
    
    async def publish(self, routing_key: str, message: bytes) -> None:
        """
        Publish a message to the broker.
        
        Args:
            routing_key: Routing key
            message: Message bytes
        """
        exchange = await self._ensure_exchange()
        await exchange.publish(message, routing_key)
    
    async def subscribe(
        self,
        queue_name: str,
        handler: Callable[[bytes], Any],
        routing_key: str = "#"
    ) -> None:
        """
        Subscribe to a queue with a message handler.
        
        Args:
            queue_name: Queue name
            handler: Message handler callback
            routing_key: Routing key pattern (default: # - all messages)
        """
        channel = await self._ensure_channel()
        exchange = await self._ensure_exchange()
        
        queue = await channel.declare_queue(queue_name)
        await queue.bind(exchange, routing_key)
        await queue.consume(handler)
        
        self._consumers[queue_name] = queue
