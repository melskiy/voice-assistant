"""
RabbitMQ client wrapper for infrastructure layer.

Business concept: Async messaging client for notification events
Implements connection management, message publishing, and consumer handling.
Offline capability: yes • CPU load: ~1% • Model size: N/A

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""
import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from datetime import datetime

import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode, IncomingMessage

logger = logging.getLogger(__name__)


@dataclass
class RabbitMQConfig:
    """Configuration for RabbitMQ connection"""
    url: str = None
    host: str = None
    port: int = None
    username: str = None
    password: str = None
    virtual_host: str = None
    exchange_name: str = None
    exchange_type: str = None
    reconnect_delay: float = None
    max_reconnect_attempts: int = None

    def __post_init__(self):
        import os
        if self.url is None:
            self.url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        if self.host is None:
            self.host = os.getenv("RABBITMQ_HOST", "localhost")
        if self.port is None:
            self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        if self.username is None:
            self.username = os.getenv("RABBITMQ_USER", "guest")
        if self.password is None:
            self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        if self.virtual_host is None:
            self.virtual_host = os.getenv("RABBITMQ_VHOST", "/")
        if self.exchange_name is None:
            self.exchange_name = os.getenv("RABBITMQ_EXCHANGE", "voice_assistant_exchange")
        if self.exchange_type is None:
            self.exchange_type = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")
        if self.reconnect_delay is None:
            self.reconnect_delay = float(os.getenv("RABBITMQ_RECONNECT_DELAY", "5.0"))
        if self.max_reconnect_attempts is None:
            self.max_reconnect_attempts = int(os.getenv("RABBITMQ_MAX_RECONNECT", "10"))


class RabbitMQClient:
    """
    RabbitMQ client wrapper with connection management.
    
    Features:
    - Automatic connection recovery
    - Message publishing with persistence
    - Consumer management with acknowledgments
    - Connection health monitoring
    """
    
    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None
        self._consumers: Dict[str, Any] = {}
        self._is_connected = False
        self._reconnect_attempts = 0
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """
        Establish connection to RabbitMQ with retry logic.
        
        Returns True if connection successful, False otherwise.
        """
        async with self._lock:
            if self._is_connected:
                return True
            
            while self._reconnect_attempts < self.config.max_reconnect_attempts:
                try:
                    logger.info(f"Connecting to RabbitMQ at {self.config.host}:{self.config.port}")
                    
                    self._connection = await aio_pika.connect_robust(
                        self.config.url,
                        host=self.config.host,
                        port=self.config.port,
                        login=self.config.username,
                        password=self.config.password,
                        virtualhost=self.config.virtual_host
                    )
                    
                    # Create channel
                    self._channel = await self._connection.channel()
                    
                    # Declare exchange
                    exchange_type_map = {
                        "direct": ExchangeType.DIRECT,
                        "topic": ExchangeType.TOPIC,
                        "fanout": ExchangeType.FANOUT,
                        "headers": ExchangeType.HEADERS
                    }
                    
                    self._exchange = await self._channel.declare_exchange(
                        self.config.exchange_name,
                        exchange_type_map[self.config.exchange_type],
                        durable=True
                    )
                    
                    self._is_connected = True
                    self._reconnect_attempts = 0
                    logger.info("RabbitMQ client connected successfully")
                    return True
                    
                except Exception as e:
                    self._reconnect_attempts += 1
                    logger.error(f"Failed to connect to RabbitMQ (attempt {self._reconnect_attempts}): {e}")
                    
                    if self._reconnect_attempts < self.config.max_reconnect_attempts:
                        await asyncio.sleep(self.config.reconnect_delay)
                    else:
                        logger.error("Max reconnection attempts reached")
                        return False
            
            return False
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection gracefully"""
        async with self._lock:
            # Cancel all consumers
            for consumer_tag in list(self._consumers.keys()):
                try:
                    await self._channel.basic_cancel(consumer_tag)
                except Exception as e:
                    logger.warning(f"Error cancelling consumer {consumer_tag}: {e}")
            
            self._consumers.clear()
            
            # Close connection
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
            
            self._is_connected = False
            self._connection = None
            self._channel = None
            self._exchange = None
            logger.info("RabbitMQ client disconnected")
    
    async def ensure_connected(self) -> bool:
        """Ensure connection is active, reconnect if necessary"""
        if not self._is_connected or self._connection is None or self._connection.is_closed:
            return await self.connect()
        return True
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return (
            self._is_connected and
            self._connection is not None and
            not self._connection.is_closed and
            self._channel is not None and
            not self._channel.is_closed
        )
    
    async def publish(
        self,
        routing_key: str,
        message_data: Dict[str, Any],
        message_type: str = "generic",
        priority: int = 0,
        headers: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish a message to RabbitMQ.
        
        Args:
            routing_key: Message routing key
            message_data: Message payload
            message_type: Type of message for categorization
            priority: Message priority (0-255)
            headers: Optional message headers
        
        Returns:
            True if message published successfully
        """
        if not await self.ensure_connected():
            logger.error("Cannot publish message: not connected to RabbitMQ")
            return False
        
        try:
            # Prepare message body
            message_body = {
                "type": message_type,
                "data": message_data,
                "timestamp": datetime.utcnow().isoformat(),
                "routing_key": routing_key
            }
            
            message = Message(
                json.dumps(message_body).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                priority=priority,
                headers=headers or {}
            )
            
            await self._exchange.publish(message, routing_key=routing_key)
            logger.debug(f"Published message to {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    async def consume(
        self,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], asyncio.coroutines],
        routing_keys: Optional[List[str]] = None,
        durable: bool = True,
        auto_ack: bool = False
    ) -> Optional[str]:
        """
        Start consuming messages from a queue.
        
        Args:
            queue_name: Name of the queue
            callback: Async callback function for message processing
            routing_keys: List of routing keys to bind
            durable: Whether queue should survive broker restart
            auto_ack: Whether to auto-acknowledge messages
        
        Returns:
            Consumer tag if successful, None otherwise
        """
        if not await self.ensure_connected():
            logger.error("Cannot consume messages: not connected to RabbitMQ")
            return None
        
        try:
            # Declare queue
            queue = await self._channel.declare_queue(
                queue_name,
                durable=durable,
                auto_delete=False
            )
            
            # Bind queue to exchange
            if routing_keys:
                for routing_key in routing_keys:
                    await queue.bind(self._exchange, routing_key=routing_key)
            else:
                await queue.bind(self._exchange, queue_name)
            
            # Define message handler
            async def message_handler(message: IncomingMessage):
                async with message.process(reject_on_redelivered=False):
                    try:
                        # Decode message
                        body = json.loads(message.body.decode())
                        
                        # Call user callback
                        await callback(body)
                        
                        # Acknowledge message
                        if not auto_ack:
                            await message.ack()
                            
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        # Reject and requeue message
                        if not auto_ack:
                            await message.reject(requeue=True)
            
            # Start consuming
            consumer_tag = await queue.consume(message_handler, no_ack=auto_ack)
            self._consumers[consumer_tag] = queue_name
            
            logger.info(f"Started consuming from queue '{queue_name}' with tag '{consumer_tag}'")
            return consumer_tag
            
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            return None
    
    async def cancel_consumer(self, consumer_tag: str) -> bool:
        """Cancel a consumer by tag"""
        if consumer_tag not in self._consumers:
            return False
        
        try:
            await self._channel.basic_cancel(consumer_tag)
            del self._consumers[consumer_tag]
            logger.info(f"Cancelled consumer '{consumer_tag}'")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel consumer: {e}")
            return False
    
    async def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        auto_delete: bool = False
    ) -> bool:
        """Declare a queue"""
        if not await self.ensure_connected():
            return False
        
        try:
            await self._channel.declare_queue(
                queue_name,
                durable=durable,
                auto_delete=auto_delete
            )
            return True
        except Exception as e:
            logger.error(f"Failed to declare queue: {e}")
            return False
    
    async def delete_queue(self, queue_name: str) -> bool:
        """Delete a queue"""
        if not await self.ensure_connected():
            return False
        
        try:
            await self._channel.queue_delete(queue_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete queue: {e}")
            return False
