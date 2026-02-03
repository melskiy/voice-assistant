"""
External service integrations module.

Provides clients for external APIs like Telegram.
"""
from .telegram_client import (
    TelegramClient,
    TelegramConfig,
    TelegramError,
    TelegramAPIError,
    TelegramRateLimitError,
    TelegramNetworkError
)

__all__ = [
    'TelegramClient',
    'TelegramConfig',
    'TelegramError',
    'TelegramAPIError',
    'TelegramRateLimitError',
    'TelegramNetworkError'
]
