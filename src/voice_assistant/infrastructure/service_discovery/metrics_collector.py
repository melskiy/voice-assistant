"""
Communication Metrics Collector

Business concept: Collects and aggregates communication metrics between
services for monitoring, analytics, and debugging.

Constraints:
- Minimal performance impact
- Configurable aggregation intervals
- Support for multiple metric types
- Export to various backends
"""

import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import logging
import json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"      # Monotonically increasing
    GAUGE = "gauge"          # Can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Time duration


@dataclass
class ServiceMetrics:
    """Metrics for a service"""
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    error_rate: float = 0.0
    requests_per_second: float = 0.0
    circuit_breaker_opens: int = 0
    fallback_count: int = 0
    retry_count: int = 0
    timeout_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def record_request(self, duration_ms: float, success: bool):
        """Record a request"""
        self.total_requests += 1
        self.total_duration_ms += duration_ms
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update timing stats
        self.min_response_time_ms = min(self.min_response_time_ms, duration_ms)
        self.max_response_time_ms = max(self.max_response_time_ms, duration_ms)
        self.avg_response_time_ms = self.total_duration_ms / self.total_requests
        
        # Update error rate
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests
        
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'service_name': self.service_name,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'avg_response_time_ms': round(self.avg_response_time_ms, 2),
            'min_response_time_ms': round(self.min_response_time_ms, 2) if self.min_response_time_ms != float('inf') else 0,
            'max_response_time_ms': round(self.max_response_time_ms, 2),
            'error_rate': round(self.error_rate, 4),
            'requests_per_second': round(self.requests_per_second, 2),
            'circuit_breaker_opens': self.circuit_breaker_opens,
            'fallback_count': self.fallback_count,
            'retry_count': self.retry_count,
            'timeout_count': self.timeout_count,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class CommunicationEvent:
    """A single communication event"""
    timestamp: datetime
    source_service: str
    target_service: str
    operation: str
    duration_ms: float
    success: bool
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'source_service': self.source_service,
            'target_service': self.target_service,
            'operation': self.operation,
            'duration_ms': round(self.duration_ms, 2),
            'success': self.success,
            'error_type': self.error_type,
            'metadata': self.metadata
        }


@dataclass
class MetricsConfig:
    """Configuration for metrics collector"""
    aggregation_interval_seconds: int = 60
    max_events_history: int = 10000
    enable_detailed_logging: bool = False
    export_enabled: bool = False
    export_endpoint: Optional[str] = None


class MetricsCollector:
    """
    Collector for service communication metrics.
    
    Collects:
    - Request counts and rates
    - Response times (avg, min, max)
    - Error rates
    - Circuit breaker events
    - Fallback usage
    - Timeout occurrences
    """
    
    def __init__(self, config: Optional[MetricsConfig] = None):
        """
        Initialize metrics collector.
        
        Args:
            config: Metrics configuration
        """
        self.config = config or MetricsConfig()
        
        # Service metrics storage
        self._service_metrics: Dict[str, ServiceMetrics] = {}
        
        # Event history
        self._events: deque = deque(maxlen=self.config.max_events_history)
        
        # Response time histograms
        self._response_times: Dict[str, List[float]] = defaultdict(list)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'events_recorded': 0,
            'metrics_calculated': 0,
            'last_aggregation': None
        }
        
        # Callbacks for real-time processing
        self._callbacks: List[Callable[[CommunicationEvent], None]] = []
        
        logger.info("Metrics collector initialized")
    
    def record_communication(
        self,
        source_service: str,
        target_service: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a service communication event.
        
        Args:
            source_service: Calling service name
            target_service: Target service name
            operation: Operation name
            duration_ms: Request duration in milliseconds
            success: Whether the request succeeded
            error_type: Type of error if failed
            metadata: Additional metadata
        """
        event = CommunicationEvent(
            timestamp=datetime.utcnow(),
            source_service=source_service,
            target_service=target_service,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type,
            metadata=metadata or {}
        )
        
        with self._lock:
            # Store event
            self._events.append(event)
            self._stats['events_recorded'] += 1
            
            # Update target service metrics
            if target_service not in self._service_metrics:
                self._service_metrics[target_service] = ServiceMetrics(
                    service_name=target_service
                )
            
            self._service_metrics[target_service].record_request(duration_ms, success)
            
            # Store response time for histogram
            self._response_times[target_service].append(duration_ms)
            
            # Update error-specific counters
            if not success:
                if error_type == 'timeout':
                    self._service_metrics[target_service].timeout_count += 1
                elif error_type == 'circuit_open':
                    self._service_metrics[target_service].circuit_breaker_opens += 1
                elif error_type == 'fallback':
                    self._service_metrics[target_service].fallback_count += 1
            
            # Update retry count from metadata
            if metadata and 'retry_count' in metadata:
                self._service_metrics[target_service].retry_count += metadata['retry_count']
        
        # Trigger callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Metrics callback error: {e}")
        
        # Detailed logging if enabled
        if self.config.enable_detailed_logging:
            logger.debug(
                f"Communication: {source_service} -> {target_service}.{operation} "
                f"({duration_ms:.2f}ms, success={success})"
            )
    
    def record_circuit_breaker_event(
        self,
        service_name: str,
        event_type: str,  # 'open', 'close', 'half_open'
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Record a circuit breaker event.
        
        Args:
            service_name: Service name
            event_type: Type of circuit breaker event
            details: Additional details
        """
        with self._lock:
            if service_name not in self._service_metrics:
                self._service_metrics[service_name] = ServiceMetrics(
                    service_name=service_name
                )
            
            if event_type == 'open':
                self._service_metrics[service_name].circuit_breaker_opens += 1
        
        if self.config.enable_detailed_logging:
            logger.info(f"Circuit breaker {event_type} for {service_name}")
    
    def record_fallback(
        self,
        service_name: str,
        fallback_type: str
    ):
        """
        Record a fallback usage.
        
        Args:
            service_name: Service name
            fallback_type: Type of fallback used
        """
        with self._lock:
            if service_name not in self._service_metrics:
                self._service_metrics[service_name] = ServiceMetrics(
                    service_name=service_name
                )
            
            self._service_metrics[service_name].fallback_count += 1
        
        if self.config.enable_detailed_logging:
            logger.info(f"Fallback used for {service_name}: {fallback_type}")
    
    def get_service_metrics(self, service_name: str) -> Optional[ServiceMetrics]:
        """Get metrics for a specific service"""
        with self._lock:
            return self._service_metrics.get(service_name)
    
    def get_all_metrics(self) -> Dict[str, ServiceMetrics]:
        """Get metrics for all services"""
        with self._lock:
            return dict(self._service_metrics)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self._lock:
            total_requests = sum(m.total_requests for m in self._service_metrics.values())
            total_success = sum(m.successful_requests for m in self._service_metrics.values())
            total_failed = sum(m.failed_requests for m in self._service_metrics.values())
            
            avg_response_time = 0.0
            if total_requests > 0:
                total_duration = sum(m.total_duration_ms for m in self._service_metrics.values())
                avg_response_time = total_duration / total_requests
            
            return {
                'total_requests': total_requests,
                'successful_requests': total_success,
                'failed_requests': total_failed,
                'overall_error_rate': total_failed / total_requests if total_requests > 0 else 0,
                'avg_response_time_ms': round(avg_response_time, 2),
                'services': {
                    name: metrics.to_dict() 
                    for name, metrics in self._service_metrics.items()
                },
                'events_recorded': self._stats['events_recorded'],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_response_time_histogram(
        self,
        service_name: str,
        buckets: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Get response time histogram for a service.
        
        Args:
            service_name: Service name
            buckets: Histogram buckets in milliseconds
            
        Returns:
            Histogram data
        """
        if buckets is None:
            buckets = [10, 50, 100, 250, 500, 1000, 2500, 5000]
        
        with self._lock:
            times = self._response_times.get(service_name, [])
        
        if not times:
            return {'service_name': service_name, 'buckets': {}, 'count': 0}
        
        histogram = {f"<{b}ms": 0 for b in buckets}
        histogram[">max"] = 0
        
        for t in times:
            placed = False
            for b in buckets:
                if t < b:
                    histogram[f"<{b}ms"] += 1
                    placed = True
                    break
            if not placed:
                histogram[">max"] += 1
        
        return {
            'service_name': service_name,
            'buckets': histogram,
            'count': len(times),
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times)
        }
    
    def get_recent_events(
        self,
        count: int = 100,
        service_filter: Optional[str] = None
    ) -> List[CommunicationEvent]:
        """
        Get recent communication events.
        
        Args:
            count: Maximum number of events
            service_filter: Filter by service name
            
        Returns:
            List of events
        """
        with self._lock:
            events = list(self._events)
        
        if service_filter:
            events = [
                e for e in events 
                if e.source_service == service_filter or e.target_service == service_filter
            ]
        
        return events[-count:]
    
    def register_callback(self, callback: Callable[[CommunicationEvent], None]):
        """Register a callback for real-time event processing"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[CommunicationEvent], None]):
        """Unregister a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def reset_metrics(self, service_name: Optional[str] = None):
        """
        Reset metrics.
        
        Args:
            service_name: Specific service to reset, or all if None
        """
        with self._lock:
            if service_name:
                if service_name in self._service_metrics:
                    del self._service_metrics[service_name]
                if service_name in self._response_times:
                    del self._response_times[service_name]
                logger.info(f"Reset metrics for {service_name}")
            else:
                self._service_metrics.clear()
                self._response_times.clear()
                self._events.clear()
                logger.info("Reset all metrics")
    
    def export_metrics(self) -> str:
        """Export metrics as JSON"""
        summary = self.get_metrics_summary()
        return json.dumps(summary, indent=2, default=str)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics"""
        return self._stats.copy()


# Global metrics collector instance
_metrics_instance: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_instance
    
    with _metrics_lock:
        if _metrics_instance is None:
            _metrics_instance = MetricsCollector()
        return _metrics_instance


class ServiceMetricsMixin:
    """
    Mixin for services to easily record metrics.
    
    Usage:
        class MyService(ServiceMetricsMixin):
            def __init__(self):
                super().__init__("my_service")
            
            async def do_something(self):
                with self.record_operation("do_something"):
                    # ... do work ...
                    pass
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._metrics = get_metrics_collector()
    
    def record_communication(
        self,
        target_service: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a communication event"""
        self._metrics.record_communication(
            source_service=self.service_name,
            target_service=target_service,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type,
            metadata=metadata
        )
    
    def record_circuit_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """Record a circuit breaker event"""
        self._metrics.record_circuit_breaker_event(
            service_name=self.service_name,
            event_type=event_type,
            details=details
        )
    
    def record_fallback(self, fallback_type: str):
        """Record a fallback usage"""
        self._metrics.record_fallback(self.service_name, fallback_type)
    
    def get_metrics(self) -> Optional[ServiceMetrics]:
        """Get metrics for this service"""
        return self._metrics.get_service_metrics(self.service_name)
