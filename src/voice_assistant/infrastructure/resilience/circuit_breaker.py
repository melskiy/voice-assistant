"""
Circuit Breaker pattern implementation.

Used to handle failures in external services gracefully.
"""
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker.
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout_seconds: Time in seconds before attempting to close circuit
        required_successes: Number of successes in half-open state to close circuit
        name: Identifier for the circuit breaker
    """
    failure_threshold: int = 5
    timeout_seconds: float = 30.0
    required_successes: int = 2
    name: str = "CircuitBreaker"


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.
    
    Provides centralized access to circuit breakers by name,
    ensuring singleton instances per service.
    """
    
    _instance = None
    _breakers: Dict[str, 'CircuitBreaker'] = {}
    
    def __new__(cls):
        """Singleton pattern to ensure single registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._breakers = {}
        return cls._instance
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> 'CircuitBreaker':
        """Get existing circuit breaker or create new one.
        
        Args:
            name: Unique identifier for the circuit breaker
            config: Configuration for new circuit breaker (if created)
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            config = config or CircuitBreakerConfig(name=name)
            self._breakers[name] = CircuitBreaker(
                failure_threshold=config.failure_threshold,
                timeout=int(config.timeout_seconds),
                name=config.name,
                required_successes=config.required_successes
            )
            logger.info(f"Created circuit breaker '{name}'")
        return self._breakers[name]
    
    def get(self, name: str) -> Optional['CircuitBreaker']:
        """Get circuit breaker by name.
        
        Args:
            name: Circuit breaker identifier
            
        Returns:
            CircuitBreaker instance or None if not found
        """
        return self._breakers.get(name)
    
    def remove(self, name: str) -> bool:
        """Remove circuit breaker from registry.
        
        Args:
            name: Circuit breaker identifier
            
        Returns:
            True if removed, False if not found
        """
        if name in self._breakers:
            del self._breakers[name]
            logger.info(f"Removed circuit breaker '{name}'")
            return True
        return False
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all registered circuit breakers.
        
        Returns:
            Dictionary mapping names to their metrics
        """
        return {
            name: breaker.get_metrics()
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers to closed state."""
        for breaker in self._breakers.values():
            breaker.force_close()
        logger.info("Reset all circuit breakers")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        timeout: int = 30,
        name: str = "CircuitBreaker",
        required_successes: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        self.required_successes = required_successes
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.success_count_in_half_open = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                logger.info(f"{self.name} transitioning to HALF_OPEN")
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count_in_half_open = 0
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count_in_half_open += 1
            if self.success_count_in_half_open >= self.required_successes:
                logger.info(f"{self.name} transitioning to CLOSED")
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitBreakerState.OPEN:
                logger.warning(
                    f"{self.name} transitioning to OPEN after "
                    f"{self.failure_count} failures"
                )
            self.state = CircuitBreakerState.OPEN
            self.success_count_in_half_open = 0
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state.value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics.
        
        Returns:
            Dictionary with current metrics
        """
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'timeout': self.timeout,
            'last_failure_time': self.last_failure_time,
            'success_count_in_half_open': self.success_count_in_half_open,
            'required_successes': self.required_successes,
            'name': self.name
        }
    
    def force_open(self):
        """Manually open the circuit breaker."""
        self.state = CircuitBreakerState.OPEN
        self.last_failure_time = time.time()
        logger.warning(f"{self.name} manually forced to OPEN")
    
    def force_close(self):
        """Manually close the circuit breaker."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count_in_half_open = 0
        self.last_failure_time = None
        logger.info(f"{self.name} manually forced to CLOSED")
