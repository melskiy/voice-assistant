"""
Resilient Service Client

Business concept: Combines circuit breaker, retry, and fallback patterns
into a unified client for making resilient service calls.

Constraints:
- Integrates all resilience patterns
- Timeout handling for all calls
- Metrics collection for monitoring
- Async/await support
"""

import asyncio
import time
from typing import Callable, Optional, Any, Dict, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
import logging

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry
from .retry_policy import RetryPolicy, RetryConfig
from .fallback_handler import FallbackHandler, FallbackConfig, FallbackResponse

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ServiceCallResult:
    """Result of a service call"""
    success: bool
    data: Any
    duration_ms: float
    attempt_count: int
    used_fallback: bool = False
    fallback_type: Optional[str] = None
    error: Optional[Exception] = None
    circuit_state: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'duration_ms': self.duration_ms,
            'attempt_count': self.attempt_count,
            'used_fallback': self.used_fallback,
            'fallback_type': self.fallback_type,
            'error': str(self.error) if self.error else None,
            'circuit_state': self.circuit_state,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ResilientClientConfig:
    """Configuration for resilient service client"""
    service_name: str
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    retry_config: Optional[RetryConfig] = None
    fallback_config: Optional[FallbackConfig] = None
    default_timeout_seconds: float = 10.0
    collect_metrics: bool = True


class ResilientServiceClient:
    """
    Service client with integrated resilience patterns.
    
    Combines:
    - Circuit breaker for preventing cascading failures
    - Retry policy for handling transient errors
    - Fallback handler for graceful degradation
    - Timeout handling for all operations
    - Metrics collection for monitoring
    
    Example:
        config = ResilientClientConfig(
            service_name="asr_service",
            default_timeout_seconds=5.0
        )
        client = ResilientServiceClient(config)
        
        result = await client.call(
            operation=asr_service.transcribe,
            audio_data=audio_chunk
        )
    """
    
    _circuit_registry = CircuitBreakerRegistry()
    
    def __init__(self, config: ResilientClientConfig):
        """
        Initialize resilient service client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        self.service_name = config.service_name
        
        # Initialize circuit breaker
        self._circuit_breaker = self._circuit_registry.get_or_create(
            config.service_name,
            config.circuit_breaker_config or CircuitBreakerConfig()
        )
        
        # Initialize retry policy
        self._retry_policy = RetryPolicy(
            config.retry_config or RetryConfig(),
            name=config.service_name
        )
        
        # Initialize fallback handler
        self._fallback_handler = FallbackHandler(
            config.service_name,
            config.fallback_config or FallbackConfig()
        )
        
        # Metrics
        self._metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'fallback_calls': 0,
            'circuit_blocked_calls': 0,
            'timeout_calls': 0,
            'total_duration_ms': 0.0
        }
        
        logger.info(f"Resilient client initialized for '{config.service_name}'")
    
    async def call(
        self,
        operation: Callable[..., T],
        *args,
        timeout_seconds: Optional[float] = None,
        fallback_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ServiceCallResult:
        """
        Execute operation with full resilience patterns.
        
        Args:
            operation: Async function to execute
            *args: Arguments for operation
            timeout_seconds: Override default timeout
            fallback_context: Context for fallback selection
            **kwargs: Keyword arguments for operation
            
        Returns:
            ServiceCallResult with operation result and metadata
        """
        start_time = time.time()
        self._metrics['total_calls'] += 1
        
        timeout = timeout_seconds or self.config.default_timeout_seconds
        fallback_context = fallback_context or {}
        
        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            self._metrics['circuit_blocked_calls'] += 1
            fallback_context['error_type'] = 'circuit_open'
            
            logger.warning(
                f"Circuit breaker blocked call to '{self.service_name}'"
            )
            
            fallback = self._fallback_handler.get_fallback(
                error=Exception("Circuit breaker open"),
                context=fallback_context
            )
            
            duration_ms = (time.time() - start_time) * 1000
            return ServiceCallResult(
                success=False,
                data=fallback.data,
                duration_ms=duration_ms,
                attempt_count=0,
                used_fallback=True,
                fallback_type=f"circuit_breaker:{fallback.fallback_type}",
                error=Exception("Circuit breaker open"),
                circuit_state=self._circuit_breaker.state.value
            )
        
        # Execute with retry and timeout
        last_error = None
        attempt_count = 0
        
        try:
            # Wrap operation with timeout
            async def operation_with_timeout():
                return await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=timeout
                )
            
            # Execute with retry
            result = await self._retry_policy.execute(operation_with_timeout)
            
            # Success
            attempt_count = self._retry_policy._attempt_count
            duration_ms = (time.time() - start_time) * 1000
            
            self._circuit_breaker.record_success()
            self._fallback_handler.record_success(result)
            
            self._metrics['successful_calls'] += 1
            self._metrics['total_duration_ms'] += duration_ms
            
            return ServiceCallResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
                attempt_count=attempt_count,
                circuit_state=self._circuit_breaker.state.value
            )
            
        except asyncio.TimeoutError as e:
            last_error = e
            self._metrics['timeout_calls'] += 1
            attempt_count = self._retry_policy._attempt_count
            
            logger.error(
                f"Timeout calling '{self.service_name}' after {timeout}s"
            )
            
        except Exception as e:
            last_error = e
            attempt_count = self._retry_policy._attempt_count
            
            logger.error(
                f"Failed to call '{self.service_name}' after {attempt_count} attempts: {e}"
            )
        
        # Record failure in circuit breaker
        self._circuit_breaker.record_failure(last_error)
        self._metrics['failed_calls'] += 1
        
        # Get fallback
        fallback_context['error_type'] = (
            'timeout' if isinstance(last_error, asyncio.TimeoutError) else 'execution_error'
        )
        
        fallback = self._fallback_handler.get_fallback(
            error=last_error,
            context=fallback_context
        )
        
        self._metrics['fallback_calls'] += 1
        
        duration_ms = (time.time() - start_time) * 1000
        self._metrics['total_duration_ms'] += duration_ms
        
        return ServiceCallResult(
            success=False,
            data=fallback.data,
            duration_ms=duration_ms,
            attempt_count=attempt_count,
            used_fallback=True,
            fallback_type=fallback.fallback_type,
            error=last_error,
            circuit_state=self._circuit_breaker.state.value
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        metrics = self._metrics.copy()
        
        # Calculate derived metrics
        if metrics['total_calls'] > 0:
            metrics['success_rate'] = metrics['successful_calls'] / metrics['total_calls']
            metrics['fallback_rate'] = metrics['fallback_calls'] / metrics['total_calls']
            metrics['avg_duration_ms'] = metrics['total_duration_ms'] / metrics['total_calls']
        else:
            metrics['success_rate'] = 0.0
            metrics['fallback_rate'] = 0.0
            metrics['avg_duration_ms'] = 0.0
        
        metrics['service_name'] = self.service_name
        metrics['circuit_state'] = self._circuit_breaker.state.value
        
        return metrics
    
    def get_circuit_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return self._circuit_breaker.get_metrics()
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get fallback handler statistics"""
        return self._fallback_handler.get_stats()
    
    def force_circuit_open(self):
        """Manually open circuit breaker"""
        self._circuit_breaker.force_open()
        logger.warning(f"Circuit breaker for '{self.service_name}' manually opened")
    
    def force_circuit_close(self):
        """Manually close circuit breaker"""
        self._circuit_breaker.force_close()
        logger.info(f"Circuit breaker for '{self.service_name}' manually closed")
    
    def reset_metrics(self):
        """Reset client metrics"""
        self._metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'fallback_calls': 0,
            'circuit_blocked_calls': 0,
            'timeout_calls': 0,
            'total_duration_ms': 0.0
        }
        logger.info(f"Metrics reset for '{self.service_name}'")


class ServiceClientFactory:
    """
    Factory for creating pre-configured resilient service clients.
    """
    
    @staticmethod
    def create_asr_client(
        timeout_seconds: float = 10.0,
        failure_threshold: int = 5
    ) -> ResilientServiceClient:
        """Create resilient client for ASR service"""
        config = ResilientClientConfig(
            service_name="asr_service",
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout_seconds=30.0
            ),
            retry_config=RetryConfig(
                max_attempts=3,
                base_delay_seconds=1.0,
                timeout_seconds=timeout_seconds
            ),
            default_timeout_seconds=timeout_seconds
        )
        return ResilientServiceClient(config)
    
    @staticmethod
    def create_nlu_client(
        timeout_seconds: float = 5.0,
        failure_threshold: int = 5
    ) -> ResilientServiceClient:
        """Create resilient client for NLU service"""
        config = ResilientClientConfig(
            service_name="nlu_service",
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout_seconds=30.0
            ),
            retry_config=RetryConfig(
                max_attempts=3,
                base_delay_seconds=0.5,
                timeout_seconds=timeout_seconds
            ),
            default_timeout_seconds=timeout_seconds
        )
        return ResilientServiceClient(config)
    
    @staticmethod
    def create_dialog_client(
        timeout_seconds: float = 5.0,
        failure_threshold: int = 5
    ) -> ResilientServiceClient:
        """Create resilient client for Dialog service"""
        config = ResilientClientConfig(
            service_name="dialog_service",
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout_seconds=30.0
            ),
            retry_config=RetryConfig(
                max_attempts=2,
                base_delay_seconds=0.5,
                timeout_seconds=timeout_seconds
            ),
            default_timeout_seconds=timeout_seconds
        )
        return ResilientServiceClient(config)
    
    @staticmethod
    def create_tts_client(
        timeout_seconds: float = 10.0,
        failure_threshold: int = 5
    ) -> ResilientServiceClient:
        """Create resilient client for TTS service"""
        config = ResilientClientConfig(
            service_name="tts_service",
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout_seconds=30.0
            ),
            retry_config=RetryConfig(
                max_attempts=2,
                base_delay_seconds=1.0,
                timeout_seconds=timeout_seconds
            ),
            default_timeout_seconds=timeout_seconds
        )
        return ResilientServiceClient(config)
    
    @staticmethod
    def create_storage_client(
        timeout_seconds: float = 5.0,
        failure_threshold: int = 5
    ) -> ResilientServiceClient:
        """Create resilient client for Storage service"""
        config = ResilientClientConfig(
            service_name="storage_service",
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout_seconds=30.0
            ),
            retry_config=RetryConfig(
                max_attempts=3,
                base_delay_seconds=1.0,
                timeout_seconds=timeout_seconds
            ),
            default_timeout_seconds=timeout_seconds
        )
        return ResilientServiceClient(config)


# Global registry for accessing all service clients
class ServiceClientRegistry:
    """
    Global registry for resilient service clients.
    """
    
    _clients: Dict[str, ResilientServiceClient] = {}
    
    @classmethod
    def register(cls, name: str, client: ResilientServiceClient):
        """Register a service client"""
        cls._clients[name] = client
    
    @classmethod
    def get(cls, name: str) -> Optional[ResilientServiceClient]:
        """Get service client by name"""
        return cls._clients.get(name)
    
    @classmethod
    def get_all_metrics(cls) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all registered clients"""
        return {
            name: client.get_metrics()
            for name, client in cls._clients.items()
        }
    
    @classmethod
    def get_all_circuit_states(cls) -> Dict[str, str]:
        """Get circuit breaker states for all clients"""
        return {
            name: client._circuit_breaker.state.value
            for name, client in cls._clients.items()
        }
    
    @classmethod
    def reset_all_metrics(cls):
        """Reset metrics for all clients"""
        for client in cls._clients.values():
            client.reset_metrics()
