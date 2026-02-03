"""
Fallback Handler Implementation

Business concept: Provides graceful degradation when services fail by
returning cached or default responses instead of failing completely.

Constraints:
- Configurable fallback strategies per service
- Cache-based fallbacks for read operations
- Static fallbacks for critical responses
- Russian language support for voice responses
"""

from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FallbackStrategy(Enum):
    """Fallback strategies"""
    STATIC = "static"           # Return static/default value
    CACHE = "cache"             # Return cached value
    LAST_KNOWN = "last_known"   # Return last successful result
    CUSTOM = "custom"           # Use custom fallback function


@dataclass
class FallbackResponse:
    """Container for fallback response data"""
    data: Any
    is_fallback: bool = True
    fallback_type: str = "unknown"
    timestamp: datetime = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'data': self.data,
            'is_fallback': self.is_fallback,
            'fallback_type': self.fallback_type,
            'timestamp': self.timestamp.isoformat(),
            'error_message': self.error_message
        }


@dataclass
class FallbackConfig:
    """Configuration for fallback handler"""
    strategy: FallbackStrategy = FallbackStrategy.STATIC
    static_value: Any = None
    cache_ttl_seconds: int = 300  # 5 minutes
    max_cache_size: int = 1000
    custom_fallback_func: Optional[Callable[..., Any]] = None


class FallbackHandler(Generic[T]):
    """
    Handler for providing fallback responses when services fail.
    
    Supports multiple fallback strategies:
    - Static: Return predefined default value
    - Cache: Return cached result from previous successful call
    - Last Known: Return the last successful result
    - Custom: Use a custom fallback function
    """
    
    # Russian voice assistant fallback responses
    DEFAULT_RESPONSES = {
        'asr_failure': 'Извините, не расслышала. Повторите, пожалуйста.',
        'nlu_failure': 'Не поняла команду. Скажите иначе или попросите помощь.',
        'dialog_failure': 'Произошла ошибка. Давайте начнём сначала.',
        'tts_failure': '',  # Silent fallback for TTS
        'storage_failure': 'Не удалось сохранить данные. Попробуйте позже.',
        'general_failure': 'Извините, временные неполадки. Повторите запрос.',
        'timeout': 'Сервис временно недоступен. Повторите через минуту.',
        'circuit_open': 'Сервис на восстановлении. Попробуйте позже.',
    }
    
    def __init__(
        self,
        name: str,
        config: Optional[FallbackConfig] = None
    ):
        """
        Initialize fallback handler.
        
        Args:
            name: Handler identifier (e.g., 'asr', 'nlu', 'dialog')
            config: Fallback configuration
        """
        self.name = name
        self.config = config or FallbackConfig()
        
        # Cache for storing successful results
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._last_known_result: Optional[T] = None
        
        # Statistics
        self._stats = {
            'fallback_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'last_fallback_time': None
        }
        
        logger.info(f"Fallback handler '{name}' initialized with {self.config.strategy.value} strategy")
    
    def get_fallback(
        self,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None
    ) -> FallbackResponse:
        """
        Get fallback response based on configured strategy.
        
        Args:
            error: The error that caused the fallback
            context: Additional context for fallback selection
            cache_key: Key for cache lookup
            
        Returns:
            Fallback response
        """
        self._stats['fallback_count'] += 1
        self._stats['last_fallback_time'] = datetime.utcnow()
        
        strategy = self.config.strategy
        error_msg = str(error) if error else None
        
        if strategy == FallbackStrategy.STATIC:
            return self._get_static_fallback(error_msg, context)
        
        elif strategy == FallbackStrategy.CACHE:
            return self._get_cache_fallback(cache_key, error_msg)
        
        elif strategy == FallbackStrategy.LAST_KNOWN:
            return self._get_last_known_fallback(error_msg)
        
        elif strategy == FallbackStrategy.CUSTOM:
            return self._get_custom_fallback(error, context)
        
        else:
            return FallbackResponse(
                data=self._get_default_response(),
                fallback_type="default",
                error_message=error_msg
            )
    
    def _get_static_fallback(
        self,
        error_msg: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> FallbackResponse:
        """Get static fallback value"""
        if self.config.static_value is not None:
            return FallbackResponse(
                data=self.config.static_value,
                fallback_type="static",
                error_message=error_msg
            )
        
        # Use default response based on context
        response = self._get_default_response(context)
        return FallbackResponse(
            data=response,
            fallback_type="static_default",
            error_message=error_msg
        )
    
    def _get_cache_fallback(
        self,
        cache_key: Optional[str],
        error_msg: Optional[str]
    ) -> FallbackResponse:
        """Get fallback from cache"""
        if cache_key and cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key)
            if timestamp and self._is_cache_valid(timestamp):
                self._stats['cache_hits'] += 1
                return FallbackResponse(
                    data=self._cache[cache_key],
                    fallback_type="cache",
                    error_message=error_msg
                )
            else:
                # Cache expired, remove it
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        
        self._stats['cache_misses'] += 1
        
        # Fall back to static
        return FallbackResponse(
            data=self._get_default_response(),
            fallback_type="cache_miss_static",
            error_message=error_msg
        )
    
    def _get_last_known_fallback(self, error_msg: Optional[str]) -> FallbackResponse:
        """Get last known successful result"""
        if self._last_known_result is not None:
            return FallbackResponse(
                data=self._last_known_result,
                fallback_type="last_known",
                error_message=error_msg
            )
        
        # Fall back to static
        return FallbackResponse(
            data=self._get_default_response(),
            fallback_type="last_known_miss_static",
            error_message=error_msg
        )
    
    def _get_custom_fallback(
        self,
        error: Optional[Exception],
        context: Optional[Dict[str, Any]]
    ) -> FallbackResponse:
        """Get fallback using custom function"""
        if self.config.custom_fallback_func:
            try:
                result = self.config.custom_fallback_func(error, context)
                return FallbackResponse(
                    data=result,
                    fallback_type="custom",
                    error_message=str(error) if error else None
                )
            except Exception as e:
                logger.error(f"Custom fallback function failed: {e}")
        
        # Fall back to static
        return FallbackResponse(
            data=self._get_default_response(context),
            fallback_type="custom_fail_static",
            error_message=str(error) if error else None
        )
    
    def _get_default_response(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get default response based on handler name and context"""
        context = context or {}
        
        # Check for specific error type
        error_type = context.get('error_type', '')
        if error_type == 'timeout':
            return self.DEFAULT_RESPONSES.get('timeout', self.DEFAULT_RESPONSES['general_failure'])
        elif error_type == 'circuit_open':
            return self.DEFAULT_RESPONSES.get('circuit_open', self.DEFAULT_RESPONSES['general_failure'])
        
        # Return handler-specific response
        return self.DEFAULT_RESPONSES.get(
            self.name,
            self.DEFAULT_RESPONSES['general_failure']
        )
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached value is still valid"""
        ttl = timedelta(seconds=self.config.cache_ttl_seconds)
        return datetime.utcnow() - timestamp < ttl
    
    def cache_result(self, key: str, result: T):
        """
        Cache a successful result for future fallback.
        
        Args:
            key: Cache key
            result: Result to cache
        """
        # Manage cache size
        if len(self._cache) >= self.config.max_cache_size:
            # Remove oldest entry
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        self._cache[key] = result
        self._cache_timestamps[key] = datetime.utcnow()
        self._last_known_result = result
        
        logger.debug(f"Cached result for key '{key}' in handler '{self.name}'")
    
    def record_success(self, result: T):
        """
        Record successful result for last_known strategy.
        
        Args:
            result: Successful result
        """
        self._last_known_result = result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fallback handler statistics"""
        return {
            'name': self.name,
            'strategy': self.config.strategy.value,
            'fallback_count': self._stats['fallback_count'],
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_size': len(self._cache),
            'last_fallback_time': (
                self._stats['last_fallback_time'].isoformat() 
                if self._stats['last_fallback_time'] else None
            ),
            'has_last_known': self._last_known_result is not None
        }
    
    def clear_cache(self):
        """Clear the cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info(f"Cache cleared for handler '{self.name}'")
    
    def get_cached_keys(self) -> list:
        """Get list of cached keys"""
        return list(self._cache.keys())


class FallbackRegistry:
    """
    Registry for managing multiple fallback handlers.
    """
    
    def __init__(self):
        self._handlers: Dict[str, FallbackHandler] = {}
    
    def register(
        self,
        name: str,
        config: Optional[FallbackConfig] = None
    ) -> FallbackHandler:
        """
        Register a fallback handler.
        
        Args:
            name: Handler name
            config: Fallback configuration
            
        Returns:
            Registered handler
        """
        handler = FallbackHandler(name, config)
        self._handlers[name] = handler
        return handler
    
    def get(self, name: str) -> Optional[FallbackHandler]:
        """Get handler by name"""
        return self._handlers.get(name)
    
    def get_fallback(
        self,
        name: str,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[FallbackResponse]:
        """
        Get fallback from specific handler.
        
        Args:
            name: Handler name
            error: Error that caused fallback
            context: Additional context
            
        Returns:
            Fallback response or None if handler not found
        """
        handler = self._handlers.get(name)
        if handler:
            return handler.get_fallback(error, context)
        return None
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all handlers"""
        return {
            name: handler.get_stats() 
            for name, handler in self._handlers.items()
        }
    
    def clear_all_caches(self):
        """Clear all handler caches"""
        for handler in self._handlers.values():
            handler.clear_cache()


# Pre-configured fallback handlers for voice assistant services

class VoiceAssistantFallbacks:
    """
    Pre-configured fallback handlers for voice assistant services.
    """
    
    @staticmethod
    def create_asr_fallback() -> FallbackHandler:
        """Create fallback handler for ASR service"""
        config = FallbackConfig(
            strategy=FallbackStrategy.STATIC,
            static_value={
                'text': '',
                'confidence': 0.0,
                'is_final': True,
                'error': 'asr_fallback'
            }
        )
        return FallbackHandler('asr', config)
    
    @staticmethod
    def create_nlu_fallback() -> FallbackHandler:
        """Create fallback handler for NLU service"""
        config = FallbackConfig(
            strategy=FallbackStrategy.STATIC,
            static_value={
                'intent': 'UNKNOWN',
                'confidence': 0.0,
                'entities': {},
                'error': 'nlu_fallback'
            }
        )
        return FallbackHandler('nlu', config)
    
    @staticmethod
    def create_dialog_fallback() -> FallbackHandler:
        """Create fallback handler for Dialog service"""
        config = FallbackConfig(
            strategy=FallbackStrategy.STATIC,
            static_value={
                'response_text': FallbackHandler.DEFAULT_RESPONSES['dialog_failure'],
                'action': 'error_recovery',
                'requires_confirmation': False,
                'session_complete': False
            }
        )
        return FallbackHandler('dialog', config)
    
    @staticmethod
    def create_tts_fallback() -> FallbackHandler:
        """Create fallback handler for TTS service"""
        config = FallbackConfig(
            strategy=FallbackStrategy.STATIC,
            static_value=b''  # Empty audio
        )
        return FallbackHandler('tts', config)
    
    @staticmethod
    def create_storage_fallback() -> FallbackHandler:
        """Create fallback handler for Storage service"""
        config = FallbackConfig(
            strategy=FallbackStrategy.STATIC,
            static_value={
                'success': False,
                'error': 'storage_fallback',
                'data': None
            }
        )
        return FallbackHandler('storage', config)
