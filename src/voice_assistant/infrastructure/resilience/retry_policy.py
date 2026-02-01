"""
Retry Policy Implementation

Business concept: Automatically retry failed operations with configurable
backoff strategies to handle transient failures.

Constraints:
- Configurable max retry attempts
- Multiple backoff strategies (exponential, linear, fixed)
- Jitter to prevent thundering herd
- Timeout handling per attempt
"""

import asyncio
import random
import time
from enum import Enum
from typing import Callable, Optional, TypeVar, Any, List, Type
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BackoffStrategy(Enum):
    """Backoff strategies for retry delays"""
    FIXED = "fixed"              # Constant delay
    LINEAR = "linear"            # Linear increase
    EXPONENTIAL = "exponential"  # Exponential increase
    DECORRELATED = "decorrelated"  # Decorrelated jitter


@dataclass
class RetryConfig:
    """Configuration for retry policy"""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_max_seconds: float = 1.0
    timeout_seconds: Optional[float] = None
    retryable_exceptions: Optional[List[Type[Exception]]] = None
    
    def __post_init__(self):
        if self.retryable_exceptions is None:
            # Default retryable exceptions
            self.retryable_exceptions = [
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
            ]


class RetryPolicy:
    """
    Retry policy for handling transient failures.
    
    Supports multiple backoff strategies with jitter to prevent
    thundering herd problems during recovery.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None, name: str = "default"):
        """
        Initialize retry policy.
        
        Args:
            config: Retry configuration
            name: Policy identifier for logging
        """
        self.config = config or RetryConfig()
        self.name = name
        self._attempt_count = 0
        self._total_delay = 0.0
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        strategy = self.config.backoff_strategy
        base = self.config.base_delay_seconds
        max_delay = self.config.max_delay_seconds
        
        if strategy == BackoffStrategy.FIXED:
            delay = base
        
        elif strategy == BackoffStrategy.LINEAR:
            delay = base * (attempt + 1)
        
        elif strategy == BackoffStrategy.EXPONENTIAL:
            delay = base * (self.config.exponential_base ** attempt)
        
        elif strategy == BackoffStrategy.DECORRELATED:
            # Decorrelated jitter: sleep = min(max_delay, random(base, sleep * 3))
            if attempt == 0:
                delay = base
            else:
                prev_delay = self.calculate_delay(attempt - 1)
                delay = min(max_delay, random.uniform(base, prev_delay * 3))
        
        else:
            delay = base
        
        # Apply cap
        delay = min(delay, max_delay)
        
        # Add jitter
        if self.config.jitter:
            jitter = random.uniform(0, self.config.jitter_max_seconds)
            delay += jitter
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        # Check max attempts
        if attempt >= self.config.max_attempts - 1:
            return False
        
        # Check if exception is retryable
        if self.config.retryable_exceptions:
            if not isinstance(exception, tuple(self.config.retryable_exceptions)):
                logger.debug(
                    f"Exception {type(exception).__name__} is not in retryable list"
                )
                return False
        
        return True
    
    async def execute(
        self,
        operation: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Async function to execute
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result from successful operation
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            self._attempt_count = attempt + 1
            
            try:
                # Apply timeout if configured
                if self.config.timeout_seconds:
                    result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=self.config.timeout_seconds
                    )
                else:
                    result = await operation(*args, **kwargs)
                
                # Success
                if attempt > 0:
                    logger.info(
                        f"Operation succeeded on attempt {attempt + 1} "
                        f"after {self._total_delay:.2f}s total delay"
                    )
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    logger.warning(
                        f"Not retrying after attempt {attempt + 1}: {e}"
                    )
                    raise
                
                # Calculate and apply delay
                delay = self.calculate_delay(attempt)
                self._total_delay += delay
                
                logger.warning(
                    f"Attempt {attempt + 1} failed for '{self.name}': {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # All attempts exhausted
        logger.error(
            f"All {self.config.max_attempts} attempts failed for '{self.name}'"
        )
        raise last_exception
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return {
            'attempt_count': self._attempt_count,
            'total_delay_seconds': self._total_delay,
            'max_attempts': self.config.max_attempts,
            'backoff_strategy': self.config.backoff_strategy.value
        }


class ExponentialBackoff:
    """
    Convenience class for exponential backoff retry policy.
    
    Common configuration for exponential backoff with jitter.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay_seconds=base_delay,
            max_delay_seconds=max_delay,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            exponential_base=exponential_base,
            jitter=jitter
        )
        self._policy = RetryPolicy(config, name="exponential_backoff")
    
    async def execute(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Execute with exponential backoff retry"""
        return await self._policy.execute(operation, *args, **kwargs)
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return self._policy.get_stats()


class LinearBackoff:
    """
    Convenience class for linear backoff retry policy.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay_seconds=base_delay,
            max_delay_seconds=max_delay,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=jitter
        )
        self._policy = RetryPolicy(config, name="linear_backoff")
    
    async def execute(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Execute with linear backoff retry"""
        return await self._policy.execute(operation, *args, **kwargs)
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return self._policy.get_stats()


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    retryable_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for adding retry logic to async functions.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        backoff_strategy: Backoff strategy to use
        retryable_exceptions: List of exceptions to retry on
        
    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def fetch_data():
            # May raise transient errors
            return await api.get_data()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay_seconds=base_delay,
            max_delay_seconds=max_delay,
            backoff_strategy=backoff_strategy,
            retryable_exceptions=retryable_exceptions
        )
        policy = RetryPolicy(config, name=func.__name__)
        
        async def wrapper(*args, **kwargs) -> T:
            return await policy.execute(func, *args, **kwargs)
        
        wrapper._retry_policy = policy
        return wrapper
    
    return decorator
