"""
RabbitMQ connection implementation.
"""

from typing import Optional, Callable, Any

try:
    import aio_pika
    from aio_pika import Message, ExchangeType
    AIO_PIKA_AVAILABLE = True
except ImportError:
    AIO_PIKA_AVAILABLE = False
    aio_pika = None
    Message = None
    ExchangeType = None

from ..interfaces import (
    IRabbitMQConnection,
    IRabbitMQChannel,
    IRabbitMQExchange,
    IRabbitMQQueue
)


class AioPikaConnection(IRabbitMQConnection):
    """
    aio-pika based RabbitMQ connection.
    """
    
    def __init__(self, url: str):
        """
        Initialize connection.
        
        Args:
            url: RabbitMQ connection URL
        """
        if not AIO_PIKA_AVAILABLE:
            raise RuntimeError("aio-pika is not installed")
        
        self._url = url
        self._connection: Optional[aio_pika.Connection] = None
    
    async def connect(self) -> None:
        """Establish connection."""
        self._connection = await aio_pika.connect_robust(self._url)
    
    async def close(self) -> None:
        """Close connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def channel(self) -> 'AioPikaChannel':
        """Get a channel."""
        if not self._connection:
            raise RuntimeError("Connection not established")
        
        ch = await self._connection.channel()
        return AioPikaChannel(ch)


class AioPikaChannel(IRabbitMQChannel):
    """
    aio-pika based RabbitMQ channel.
    """
    
    def __init__(self, channel: aio_pika.Channel):
        """
        Initialize channel.
        
        Args:
            channel: aio-pika channel
        """
        self._channel = channel
    
    async def declare_exchange(
        self,
        name: str,
        exchange_type: str
    ) -> 'AioPikaExchange':
        """Declare an exchange."""
        exchange_type_enum = getattr(ExchangeType, exchange_type.upper(), ExchangeType.TOPIC)
        exchange = await self._channel.declare_exchange(name, exchange_type_enum)
        return AioPikaExchange(exchange)
    
    async def declare_queue(self, name: str) -> 'AioPikaQueue':
        """Declare a queue."""
        queue = await self._channel.declare_queue(name)
        return AioPikaQueue(queue)
    
    async def close(self) -> None:
        """Close channel."""
        await self._channel.close()


class AioPikaExchange(IRabbitMQExchange):
    """
    aio-pika based RabbitMQ exchange.
    """
    
    def __init__(self, exchange: aio_pika.Exchange):
        """
        Initialize exchange.
        
        Args:
            exchange: aio-pika exchange
        """
        self._exchange = exchange
    
    async def publish(
        self,
        message: bytes,
        routing_key: str
    ) -> None:
        """Publish a message."""
        await self._exchange.publish(
            Message(message),
            routing_key=routing_key
        )


class AioPikaQueue(IRabbitMQQueue):
    """
    aio-pika based RabbitMQ queue.
    """
    
    def __init__(self, queue: aio_pika.Queue):
        """
        Initialize queue.
        
        Args:
            queue: aio-pika queue
        """
        self._queue = queue
    
    async def bind(
        self,
        exchange: IRabbitMQExchange,
        routing_key: str
    ) -> None:
        """Bind queue to exchange."""
        if isinstance(exchange, AioPikaExchange):
            await self._queue.bind(exchange._exchange, routing_key)
    
    async def consume(
        self,
        callback: Callable[[bytes], Any]
    ) -> None:
        """Start consuming messages."""
        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                await callback(message.body)
        
        await self._queue.consume(on_message)


class RabbitMQConnectionFactory:
    """
    Factory for creating RabbitMQ connections.
    """
    
    @staticmethod
    def create(config: dict) -> AioPikaConnection:
        """
        Create a RabbitMQ connection from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configured connection
        """
        url = config.get("url")
        
        if not url:
            # Build URL from components
            host = config.get("host", "localhost")
            port = config.get("port", 5672)
            username = config.get("username", "guest")
            password = config.get("password", "guest")
            virtual_host = config.get("virtual_host", "/")
            
            url = f"amqp://{username}:{password}@{host}:{port}{virtual_host}"
        
        return AioPikaConnection(url)
