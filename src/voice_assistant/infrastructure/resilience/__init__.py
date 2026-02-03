"""
Resilience patterns for the voice assistant core.
Implements circuit breaker, retry, and fallback patterns for fault tolerance.
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerRegistry
)
from .retry_policy import RetryPolicy, ExponentialBackoff
from .fallback_handler import FallbackHandler, FallbackResponse
from .service_client import ResilientServiceClient

__all__ = [
    'CircuitBreaker',
    'CircuitBreakerState',
    'CircuitBreakerConfig',
    'CircuitBreakerRegistry',
    'RetryPolicy',
    'ExponentialBackoff',
    'FallbackHandler',
    'FallbackResponse',
    'ResilientServiceClient',
]
