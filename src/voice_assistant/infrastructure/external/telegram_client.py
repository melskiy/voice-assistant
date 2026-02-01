"""
Telegram Bot API client wrapper with retry logic.

Business concept: External API client for Telegram message delivery
Implements exponential backoff retry for API failures.
Offline capability: no (requires Telegram API) • CPU load: ~1% • Model size: N/A

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """Base exception for Telegram API errors"""
    pass


class TelegramAPIError(TelegramError):
    """Telegram API returned an error"""
    def __init__(self, error_code: int, description: str):
        self.error_code = error_code
        self.description = description
        super().__init__(f"Telegram API Error {error_code}: {description}")


class TelegramRateLimitError(TelegramError):
    """Rate limit exceeded"""
    pass


class TelegramNetworkError(TelegramError):
    """Network error during API call"""
    pass


@dataclass
class TelegramConfig:
    """Configuration for Telegram Bot API"""
    bot_token: str
    base_url: str = "https://api.telegram.org"
    timeout: float = 30.0
    max_retries: int = 5
    base_retry_delay: float = 1.0
    max_retry_delay: float = 60.0


class TelegramClient:
    """
    Telegram Bot API client with exponential backoff retry logic.
    
    Features:
    - Message sending with retry
    - Exponential backoff for failures
    - Rate limit handling
    - Connection pooling
    """
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_url = f"{config.base_url}/bot{config.bot_token}"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        return self._session
    
    async def close(self) -> None:
        """Close the client session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Telegram API with retry logic.
        
        Implements exponential backoff for transient failures.
        """
        session = await self._get_session()
        url = f"{self._api_url}/{endpoint}"
        
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                async with session.post(url, json=data) as response:
                    response_data = await response.json()
                    
                    if response.status == 429:
                        # Rate limit - get retry_after from response
                        retry_after = response_data.get('parameters', {}).get('retry_after', 30)
                        logger.warning(f"Rate limited by Telegram. Retry after {retry_after}s")
                        raise TelegramRateLimitError(f"Rate limited. Retry after {retry_after}s")
                    
                    if response.status >= 500:
                        # Server error - retry
                        raise TelegramNetworkError(f"Server error {response.status}")
                    
                    if not response_data.get('ok'):
                        # API returned error
                        error_code = response_data.get('error_code', 0)
                        description = response_data.get('description', 'Unknown error')
                        raise TelegramAPIError(error_code, description)
                    
                    return response_data
                    
            except TelegramRateLimitError:
                # Don't retry rate limits immediately
                raise
                
            except (TelegramNetworkError, aiohttp.ClientError) as e:
                last_exception = e
                
                if attempt < self.config.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = min(
                        self.config.base_retry_delay * (2 ** attempt),
                        self.config.max_retry_delay
                    )
                    logger.warning(
                        f"Telegram API request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded for Telegram API request: {e}")
                    raise TelegramNetworkError(f"Failed after {self.config.max_retries} attempts: {e}")
            
            except TelegramAPIError:
                # Don't retry client errors (4xx)
                raise
        
        raise last_exception or TelegramError("Unknown error")
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: Optional[str] = None,
        disable_notification: bool = False,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a text message to a chat.
        
        Args:
            chat_id: Target chat ID or username
            text: Message text (max 4096 characters)
            parse_mode: Parsing mode (HTML, Markdown, MarkdownV2)
            disable_notification: Send silently
            reply_markup: Additional interface options
        
        Returns:
            API response containing message info
        
        Raises:
            TelegramAPIError: If API returns an error
            TelegramNetworkError: If network issues persist after retries
        """
        data = {
            "chat_id": chat_id,
            "text": text[:4096],  # Telegram message limit
            "disable_notification": disable_notification
        }
        
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        try:
            result = await self._make_request("POST", "sendMessage", data)
            logger.info(f"Message sent successfully to chat {chat_id}")
            return result
            
        except TelegramRateLimitError as e:
            logger.error(f"Rate limit hit for chat {chat_id}: {e}")
            raise
        except TelegramAPIError as e:
            logger.error(f"Telegram API error for chat {chat_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending message to {chat_id}: {e}")
            raise TelegramError(f"Failed to send message: {e}")
    
    async def get_me(self) -> Dict[str, Any]:
        """
        Get information about the bot.
        
        Returns:
            Bot information
        """
        return await self._make_request("POST", "getMe", {})
    
    async def validate_token(self) -> bool:
        """
        Validate the bot token by making a test API call.
        
        Returns:
            True if token is valid
        """
        try:
            result = await self.get_me()
            bot_info = result.get('result', {})
            logger.info(f"Token validated. Bot: @{bot_info.get('username')}")
            return True
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    async def send_notification(
        self,
        recipient_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a notification message with metadata handling.
        
        This is a higher-level method that wraps send_message
        with notification-specific logic.
        
        Args:
            recipient_id: Target recipient (chat_id)
            message: Notification message
            metadata: Optional metadata for the notification
        
        Returns:
            API response with message details including message_id
        """
        # Build message with optional metadata
        full_message = message
        
        if metadata:
            # Add metadata as footer if present
            footer_parts = []
            if 'reminder_id' in metadata:
                footer_parts.append(f"Reminder ID: {metadata['reminder_id']}")
            if 'session_id' in metadata:
                footer_parts.append(f"Session: {metadata['session_id']}")
            
            if footer_parts:
                full_message += "\n\n" + " | ".join(footer_parts)
        
        result = await self.send_message(
            chat_id=recipient_id,
            text=full_message,
            parse_mode="HTML",
            disable_notification=False
        )
        
        return result
