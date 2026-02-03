"""
Dependency Injection Container for Notification Service.
Configures messaging, external clients, and repositories using DDD principles.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""
import os
import logging
from typing import Optional

from rodi import Container

from voice_assistant.domain.repositories import INotificationRepository
from voice_assistant.infrastructure.external import TelegramClient, TelegramConfig
from voice_assistant.infrastructure.messaging import RabbitMQClient, RabbitMQConfig
from voice_assistant.infrastructure.persistence import DatabaseConnectionPool, DatabaseConfig, \
    PostgresNotificationRepository

logger = logging.getLogger(__name__)


class NotificationServiceContainer:
    """
    IoC Container for Notification Service.
    
    Manages dependency injection for:
    - RabbitMQ messaging client
    - Telegram bot client
    - Notification repository
    - Database connection pool
    """
    
    def __init__(self):
        self._container = Container()
        self._is_configured = False
        self._db_pool: Optional[DatabaseConnectionPool] = None
        self._rabbitmq_client: Optional[RabbitMQClient] = None
        self._telegram_client: Optional[TelegramClient] = None
    
    def configure(
        self,
        db_config: Optional[DatabaseConfig] = None,
        rabbitmq_config: Optional[RabbitMQConfig] = None,
        telegram_config: Optional[TelegramConfig] = None
    ) -> None:
        """Configure the container with dependencies"""
        if self._is_configured:
            return
        
        # Create configs from environment if not provided
        if db_config is None:
            db_config = self._create_db_config_from_env()
        
        if rabbitmq_config is None:
            rabbitmq_config = self._create_rabbitmq_config_from_env()
        
        if telegram_config is None:
            telegram_config = self._create_telegram_config_from_env()
        
        # Register database connection pool as singleton
        self._db_pool = DatabaseConnectionPool(db_config)
        self._container.add_singleton(
            DatabaseConnectionPool,
            self._db_pool
        )
        
        # Register RabbitMQ client as singleton
        self._rabbitmq_client = RabbitMQClient(rabbitmq_config)
        self._container.add_singleton(
            RabbitMQClient,
            self._rabbitmq_client
        )
        
        # Register Telegram client as singleton (if token is provided)
        if telegram_config.bot_token:
            self._telegram_client = TelegramClient(telegram_config)
            self._container.add_singleton(
                TelegramClient,
                self._telegram_client
            )
        
        # Register notification repository
        self._container.add_singleton(
            INotificationRepository,
            PostgresNotificationRepository(self._db_pool)
        )
        
        self._is_configured = True
        logger.info("Notification service container configured")
    
    def _create_db_config_from_env(self) -> DatabaseConfig:
        """Create database config from environment variables"""
        return DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'voice_assistant'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            min_pool_size=int(os.getenv('DB_MIN_POOL_SIZE', '5')),
            max_pool_size=int(os.getenv('DB_MAX_POOL_SIZE', '20')),
            command_timeout=int(os.getenv('DB_COMMAND_TIMEOUT', '60'))
        )
    
    def _create_rabbitmq_config_from_env(self) -> RabbitMQConfig:
        """Create RabbitMQ config from environment variables"""
        return RabbitMQConfig(
            url=os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/'),
            host=os.getenv('RABBITMQ_HOST', 'localhost'),
            port=int(os.getenv('RABBITMQ_PORT', '5672')),
            username=os.getenv('RABBITMQ_USER', 'guest'),
            password=os.getenv('RABBITMQ_PASSWORD', 'guest'),
            virtual_host=os.getenv('RABBITMQ_VHOST', '/'),
            exchange_name=os.getenv('RABBITMQ_EXCHANGE', 'voice_assistant_exchange'),
            exchange_type=os.getenv('RABBITMQ_EXCHANGE_TYPE', 'topic'),
            reconnect_delay=float(os.getenv('RABBITMQ_RECONNECT_DELAY', '5.0')),
            max_reconnect_attempts=int(os.getenv('RABBITMQ_MAX_RECONNECT', '10'))
        )
    
    def _create_telegram_config_from_env(self) -> TelegramConfig:
        """Create Telegram config from environment variables"""
        return TelegramConfig(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            base_url=os.getenv('TELEGRAM_API_URL', 'https://api.telegram.org'),
            timeout=float(os.getenv('TELEGRAM_TIMEOUT', '30.0')),
            max_retries=int(os.getenv('TELEGRAM_MAX_RETRIES', '5')),
            base_retry_delay=float(os.getenv('TELEGRAM_RETRY_DELAY', '1.0')),
            max_retry_delay=float(os.getenv('TELEGRAM_MAX_RETRY_DELAY', '60.0'))
        )
    
    def get_notification_repository(self) -> INotificationRepository:
        """Get notification repository instance"""
        if not self._is_configured:
            self.configure()
        return self._container.resolve(INotificationRepository)
    
    def get_rabbitmq_client(self) -> RabbitMQClient:
        """Get RabbitMQ client instance"""
        if not self._is_configured:
            self.configure()
        return self._container.resolve(RabbitMQClient)
    
    def get_telegram_client(self) -> Optional[TelegramClient]:
        """Get Telegram client instance"""
        if not self._is_configured:
            self.configure()
        try:
            return self._container.resolve(TelegramClient)
        except:
            return None
    
    def get_db_pool(self) -> DatabaseConnectionPool:
        """Get database connection pool"""
        if not self._is_configured:
            self.configure()
        return self._container.resolve(DatabaseConnectionPool)
    
    async def initialize(self) -> None:
        """Initialize all connections"""
        if not self._is_configured:
            self.configure()
        
        # Initialize database
        if self._db_pool:
            await self._db_pool.initialize()
            logger.info("Notification service database initialized")
        
        # Initialize RabbitMQ connection
        if self._rabbitmq_client:
            connected = await self._rabbitmq_client.connect()
            if connected:
                logger.info("Notification service RabbitMQ connected")
            else:
                logger.error("Failed to connect to RabbitMQ")
        
        # Validate Telegram token (optional)
        if self._telegram_client:
            is_valid = await self._telegram_client.validate_token()
            if is_valid:
                logger.info("Telegram bot token validated")
            else:
                logger.warning("Telegram bot token validation failed")
    
    async def shutdown(self) -> None:
        """Shutdown all connections"""
        # Close RabbitMQ connection
        if self._rabbitmq_client:
            await self._rabbitmq_client.disconnect()
            logger.info("Notification service RabbitMQ disconnected")
        
        # Close Telegram client
        if self._telegram_client:
            await self._telegram_client.close()
            logger.info("Telegram client closed")
        
        # Close database pool
        if self._db_pool:
            await self._db_pool.close()
            logger.info("Notification service database shutdown")


# Global container instance
_container_instance: Optional[NotificationServiceContainer] = None


def get_container() -> NotificationServiceContainer:
    """Get or create the global container instance"""
    global _container_instance
    if _container_instance is None:
        _container_instance = NotificationServiceContainer()
    return _container_instance
