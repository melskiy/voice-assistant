"""
Health Checker Implementation

Business concept: Performs health checks on services and updates
their status in the service registry.

Constraints:
- Configurable health check intervals
- Multiple health check types (HTTP, gRPC, TCP)
- Grace period for startup
- Automatic status updates
"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
import time

import grpc
import aiohttp

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"  # Partial functionality
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    message: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'details': self.details
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""
    check_interval_seconds: float = 10.0
    timeout_seconds: float = 5.0
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    startup_grace_period_seconds: float = 30.0


class HealthChecker:
    """
    Performs health checks on services.
    
    Supports multiple check types:
    - HTTP/REST endpoints
    - gRPC health checks
    - TCP connection checks
    - Custom check functions
    """
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """
        Initialize health checker.
        
        Args:
            config: Health check configuration
        """
        self.config = config or HealthCheckConfig()
        self._checks: Dict[str, Dict[str, Any]] = {}
        self._check_tasks: Dict[str, asyncio.Task] = {}
        self._lock = threading.Lock()
        self._running = False
        
        # Statistics
        self._stats = {
            'checks_performed': 0,
            'healthy_results': 0,
            'unhealthy_results': 0,
            'check_errors': 0
        }
        
        logger.info("Health checker initialized")
    
    def register_http_check(
        self,
        service_name: str,
        instance_id: str,
        url: str,
        expected_status: int = 200,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Register an HTTP health check.
        
        Args:
            service_name: Service name
            instance_id: Instance identifier
            url: Health check URL
            expected_status: Expected HTTP status code
            headers: Optional request headers
        """
        with self._lock:
            self._checks[instance_id] = {
                'type': 'http',
                'service_name': service_name,
                'instance_id': instance_id,
                'url': url,
                'expected_status': expected_status,
                'headers': headers or {},
                'consecutive_failures': 0,
                'consecutive_successes': 0,
                'current_status': HealthStatus.UNKNOWN,
                'registered_at': time.time()
            }
            logger.debug(f"Registered HTTP health check for {service_name} instance {instance_id}")
    
    def register_grpc_check(
        self,
        service_name: str,
        instance_id: str,
        host: str,
        port: int,
        service_name_grpc: Optional[str] = None
    ):
        """
        Register a gRPC health check.
        
        Args:
            service_name: Service name
            instance_id: Instance identifier
            host: gRPC service host
            port: gRPC service port
            service_name_grpc: Specific gRPC service to check (optional)
        """
        with self._lock:
            self._checks[instance_id] = {
                'type': 'grpc',
                'service_name': service_name,
                'instance_id': instance_id,
                'host': host,
                'port': port,
                'service_name_grpc': service_name_grpc,
                'consecutive_failures': 0,
                'consecutive_successes': 0,
                'current_status': HealthStatus.UNKNOWN,
                'registered_at': time.time()
            }
            logger.debug(f"Registered gRPC health check for {service_name} instance {instance_id}")
    
    def register_tcp_check(
        self,
        service_name: str,
        instance_id: str,
        host: str,
        port: int
    ):
        """
        Register a TCP connection health check.
        
        Args:
            service_name: Service name
            instance_id: Instance identifier
            host: Service host
            port: Service port
        """
        with self._lock:
            self._checks[instance_id] = {
                'type': 'tcp',
                'service_name': service_name,
                'instance_id': instance_id,
                'host': host,
                'port': port,
                'consecutive_failures': 0,
                'consecutive_successes': 0,
                'current_status': HealthStatus.UNKNOWN,
                'registered_at': time.time()
            }
            logger.debug(f"Registered TCP health check for {service_name} instance {instance_id}")
    
    def register_custom_check(
        self,
        service_name: str,
        instance_id: str,
        check_func: Callable[[], asyncio.Future[HealthCheckResult]]
    ):
        """
        Register a custom health check function.
        
        Args:
            service_name: Service name
            instance_id: Instance identifier
            check_func: Async function that returns HealthCheckResult
        """
        with self._lock:
            self._checks[instance_id] = {
                'type': 'custom',
                'service_name': service_name,
                'instance_id': instance_id,
                'check_func': check_func,
                'consecutive_failures': 0,
                'consecutive_successes': 0,
                'current_status': HealthStatus.UNKNOWN,
                'registered_at': time.time()
            }
            logger.debug(f"Registered custom health check for {service_name} instance {instance_id}")
    
    def unregister_check(self, instance_id: str) -> bool:
        """
        Unregister a health check.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            True if unregistered, False if not found
        """
        with self._lock:
            if instance_id not in self._checks:
                return False
            
            # Cancel running task if any
            if instance_id in self._check_tasks:
                self._check_tasks[instance_id].cancel()
                del self._check_tasks[instance_id]
            
            del self._checks[instance_id]
            logger.debug(f"Unregistered health check for instance {instance_id}")
            return True
    
    async def _check_http(self, check_config: Dict[str, Any]) -> HealthCheckResult:
        """Perform HTTP health check"""
        start_time = time.time()
        url = check_config['url']
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    url, 
                    headers=check_config.get('headers', {})
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status == check_config['expected_status']:
                        return HealthCheckResult(
                            status=HealthStatus.HEALTHY,
                            response_time_ms=response_time_ms,
                            timestamp=datetime.utcnow(),
                            message=f"HTTP {response.status}",
                            details={'status_code': response.status}
                        )
                    else:
                        return HealthCheckResult(
                            status=HealthStatus.UNHEALTHY,
                            response_time_ms=response_time_ms,
                            timestamp=datetime.utcnow(),
                            message=f"Unexpected status: {response.status}",
                            details={'expected': check_config['expected_status'], 'actual': response.status}
                        )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                message="HTTP check timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                message=f"HTTP check error: {str(e)}"
            )
    
    async def _check_grpc(self, check_config: Dict[str, Any]) -> HealthCheckResult:
        """Perform gRPC health check"""
        start_time = time.time()
        host = check_config['host']
        port = check_config['port']
        address = f"{host}:{port}"
        
        try:
            # Create channel with timeout
            channel = grpc.aio.insecure_channel(address)
            
            # Check channel connectivity
            try:
                await asyncio.wait_for(
                    channel.channel_ready(),
                    timeout=self.config.timeout_seconds
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                await channel.close()
                
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow(),
                    message="gRPC channel ready",
                    details={'address': address}
                )
            
            except asyncio.TimeoutError:
                await channel.close()
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.utcnow(),
                    message="gRPC channel timeout"
                )
        
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                message=f"gRPC check error: {str(e)}"
            )
    
    async def _check_tcp(self, check_config: Dict[str, Any]) -> HealthCheckResult:
        """Perform TCP connection health check"""
        start_time = time.time()
        host = check_config['host']
        port = check_config['port']
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.config.timeout_seconds
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            writer.close()
            await writer.wait_closed()
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                message=f"TCP connection successful to {host}:{port}",
                details={'host': host, 'port': port}
            )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                message=f"TCP connection timeout to {host}:{port}"
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                message=f"TCP connection error: {str(e)}"
            )
    
    async def _perform_check(self, instance_id: str) -> HealthCheckResult:
        """Perform health check based on type"""
        with self._lock:
            check_config = self._checks.get(instance_id)
        
        if not check_config:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                message="Check configuration not found"
            )
        
        check_type = check_config['type']
        
        if check_type == 'http':
            return await self._check_http(check_config)
        elif check_type == 'grpc':
            return await self._check_grpc(check_config)
        elif check_type == 'tcp':
            return await self._check_tcp(check_config)
        elif check_type == 'custom':
            try:
                return await check_config['check_func']()
            except Exception as e:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    timestamp=datetime.utcnow(),
                    message=f"Custom check error: {str(e)}"
                )
        else:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                message=f"Unknown check type: {check_type}"
            )
    
    async def _check_loop(self, instance_id: str):
        """Continuous health check loop for an instance"""
        while self._running:
            try:
                result = await self._perform_check(instance_id)
                await self._process_result(instance_id, result)
                
                await asyncio.sleep(self.config.check_interval_seconds)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop for {instance_id}: {e}")
                await asyncio.sleep(self.config.check_interval_seconds)
    
    async def _process_result(self, instance_id: str, result: HealthCheckResult):
        """Process health check result and update status"""
        with self._lock:
            if instance_id not in self._checks:
                return
            
            check_config = self._checks[instance_id]
            
            # Update statistics
            self._stats['checks_performed'] += 1
            if result.status == HealthStatus.HEALTHY:
                self._stats['healthy_results'] += 1
            else:
                self._stats['unhealthy_results'] += 1
            
            # Update consecutive counters
            if result.status == HealthStatus.HEALTHY:
                check_config['consecutive_successes'] += 1
                check_config['consecutive_failures'] = 0
            else:
                check_config['consecutive_failures'] += 1
                check_config['consecutive_successes'] = 0
            
            # Determine status change
            old_status = check_config['current_status']
            new_status = old_status
            
            # Check if still in grace period
            time_since_registration = time.time() - check_config['registered_at']
            in_grace_period = time_since_registration < self.config.startup_grace_period_seconds
            
            if in_grace_period and old_status == HealthStatus.UNKNOWN:
                # During grace period, be more lenient
                if check_config['consecutive_successes'] >= 1:
                    new_status = HealthStatus.HEALTHY
            else:
                # Normal operation
                if check_config['consecutive_failures'] >= self.config.unhealthy_threshold:
                    new_status = HealthStatus.UNHEALTHY
                elif check_config['consecutive_successes'] >= self.config.healthy_threshold:
                    new_status = HealthStatus.HEALTHY
            
            check_config['current_status'] = new_status
            
            if old_status != new_status:
                logger.info(
                    f"Health status changed for {check_config['service_name']} "
                    f"instance {instance_id}: {old_status.value} -> {new_status.value}"
                )
    
    def start(self):
        """Start health checker"""
        if self._running:
            return
        
        self._running = True
        
        # Start check loops for all registered checks
        for instance_id in self._checks:
            task = asyncio.create_task(self._check_loop(instance_id))
            self._check_tasks[instance_id] = task
        
        logger.info("Health checker started")
    
    def stop(self):
        """Stop health checker"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all check tasks
        for task in self._check_tasks.values():
            task.cancel()
        
        self._check_tasks.clear()
        
        logger.info("Health checker stopped")
    
    def get_status(self, instance_id: str) -> Optional[HealthStatus]:
        """Get current health status for an instance"""
        with self._lock:
            check = self._checks.get(instance_id)
            if check:
                return check['current_status']
            return None
    
    def get_all_statuses(self) -> Dict[str, HealthStatus]:
        """Get all health statuses"""
        with self._lock:
            return {
                id: check['current_status'] 
                for id, check in self._checks.items()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get health checker statistics"""
        return self._stats.copy()
