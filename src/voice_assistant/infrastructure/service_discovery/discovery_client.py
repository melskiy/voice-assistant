"""
Service Discovery Client

Business concept: Client for discovering service endpoints from the
service registry with load balancing and failover support.

Constraints:
- Caching of discovered endpoints
- Automatic failover to healthy instances
- Load balancing strategies
- Integration with resilient service client
"""

import asyncio
import random
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

from .service_registry import ServiceRegistry, ServiceInstance, ServiceStatus, get_service_registry

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"


@dataclass
class ServiceEndpoint:
    """Discovered service endpoint"""
    service_name: str
    host: str
    port: int
    instance_id: str
    metadata: Dict[str, Any]
    discovered_at: datetime
    
    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.utcnow()
    
    def get_address(self) -> str:
        """Get endpoint address"""
        return f"{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'service_name': self.service_name,
            'host': self.host,
            'port': self.port,
            'instance_id': self.instance_id,
            'metadata': self.metadata,
            'address': self.get_address(),
            'discovered_at': self.discovered_at.isoformat()
        }


@dataclass
class DiscoveryConfig:
    """Configuration for service discovery"""
    cache_ttl_seconds: int = 30
    refresh_interval_seconds: int = 10
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    failover_enabled: bool = True
    max_retries: int = 3


class DiscoveryClient:
    """
    Client for discovering and connecting to services.
    
    Features:
    - Service endpoint discovery from registry
    - Local caching with TTL
    - Load balancing across healthy instances
    - Automatic failover
    """
    
    def __init__(
        self,
        registry: Optional[ServiceRegistry] = None,
        config: Optional[DiscoveryConfig] = None
    ):
        """
        Initialize discovery client.
        
        Args:
            registry: Service registry to use (defaults to global)
            config: Discovery configuration
        """
        self.registry = registry or get_service_registry()
        self.config = config or DiscoveryConfig()
        
        # Cache for discovered endpoints
        self._cache: Dict[str, List[ServiceEndpoint]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._round_robin_counters: Dict[str, int] = {}
        
        # Statistics
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'discoveries': 0,
            'failovers': 0,
            'no_endpoints': 0
        }
        
        logger.info("Discovery client initialized")
    
    async def discover(
        self,
        service_name: str,
        force_refresh: bool = False
    ) -> List[ServiceEndpoint]:
        """
        Discover endpoints for a service.
        
        Args:
            service_name: Service to discover
            force_refresh: Force refresh from registry
            
        Returns:
            List of healthy service endpoints
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid(service_name):
            self._stats['cache_hits'] += 1
            return self._cache[service_name]
        
        self._stats['cache_misses'] += 1
        
        # Fetch from registry
        service_info = self.registry.get_service(service_name)
        
        endpoints = []
        for instance in service_info.instances:
            # Only include healthy, non-expired instances
            if (instance.status == ServiceStatus.HEALTHY and 
                not instance.is_expired()):
                endpoint = ServiceEndpoint(
                    service_name=service_name,
                    host=instance.host,
                    port=instance.port,
                    instance_id=instance.instance_id,
                    metadata=instance.metadata,
                    discovered_at=datetime.utcnow()
                )
                endpoints.append(endpoint)
        
        # Update cache
        self._cache[service_name] = endpoints
        self._cache_timestamps[service_name] = datetime.utcnow()
        self._stats['discoveries'] += 1
        
        logger.debug(f"Discovered {len(endpoints)} endpoints for {service_name}")
        
        return endpoints
    
    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if cached endpoints are still valid"""
        if service_name not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[service_name]
        ttl = timedelta(seconds=self.config.cache_ttl_seconds)
        
        return datetime.utcnow() - timestamp < ttl
    
    async def get_endpoint(
        self,
        service_name: str,
        strategy: Optional[LoadBalancingStrategy] = None
    ) -> Optional[ServiceEndpoint]:
        """
        Get a single endpoint for a service using load balancing.
        
        Args:
            service_name: Service to discover
            strategy: Load balancing strategy (uses default if None)
            
        Returns:
            Service endpoint or None if no healthy instances
        """
        endpoints = await self.discover(service_name)
        
        if not endpoints:
            self._stats['no_endpoints'] += 1
            logger.warning(f"No healthy endpoints found for {service_name}")
            return None
        
        strategy = strategy or self.config.load_balancing_strategy
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, endpoints)
        elif strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(endpoints)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(endpoints)
        else:
            # Default to round robin
            return self._round_robin_select(service_name, endpoints)
    
    def _round_robin_select(
        self,
        service_name: str,
        endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Select endpoint using round-robin"""
        counter = self._round_robin_counters.get(service_name, 0)
        endpoint = endpoints[counter % len(endpoints)]
        self._round_robin_counters[service_name] = (counter + 1) % len(endpoints)
        return endpoint
    
    def _least_connections_select(
        self,
        endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Select endpoint with least connections (based on metadata)"""
        # Sort by connection count in metadata (default to 0)
        sorted_endpoints = sorted(
            endpoints,
            key=lambda e: e.metadata.get('connection_count', 0)
        )
        return sorted_endpoints[0]
    
    async def call_with_failover(
        self,
        service_name: str,
        operation: Callable[[ServiceEndpoint], Any],
        max_retries: Optional[int] = None
    ) -> Any:
        """
        Call an operation with automatic failover to other endpoints.
        
        Args:
            service_name: Service to call
            operation: Async function that takes an endpoint
            max_retries: Maximum number of failover attempts
            
        Returns:
            Operation result
            
        Raises:
            Exception if all endpoints fail
        """
        max_retries = max_retries or self.config.max_retries
        endpoints = await self.discover(service_name)
        
        if not endpoints:
            raise Exception(f"No healthy endpoints available for {service_name}")
        
        last_error = None
        
        for i, endpoint in enumerate(endpoints[:max_retries]):
            try:
                result = await operation(endpoint)
                
                if i > 0:
                    self._stats['failovers'] += 1
                    logger.info(
                        f"Failover successful for {service_name} on attempt {i + 1}"
                    )
                
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Endpoint {endpoint.get_address()} failed for {service_name}: {e}"
                )
                
                # Mark endpoint as potentially unhealthy
                await self._mark_endpoint_unhealthy(endpoint)
        
        # All endpoints failed
        raise Exception(
            f"All endpoints failed for {service_name}. Last error: {last_error}"
        )
    
    async def _mark_endpoint_unhealthy(self, endpoint: ServiceEndpoint):
        """Mark an endpoint as potentially unhealthy"""
        # This would integrate with the health checker
        # For now, just invalidate cache to force rediscovery
        if endpoint.service_name in self._cache:
            del self._cache[endpoint.service_name]
            del self._cache_timestamps[endpoint.service_name]
    
    def invalidate_cache(self, service_name: Optional[str] = None):
        """
        Invalidate cached endpoints.
        
        Args:
            service_name: Specific service to invalidate, or all if None
        """
        if service_name:
            if service_name in self._cache:
                del self._cache[service_name]
                del self._cache_timestamps[service_name]
                logger.debug(f"Invalidated cache for {service_name}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.debug("Invalidated all discovery caches")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get discovery client statistics"""
        stats = self._stats.copy()
        stats['cached_services'] = len(self._cache)
        return stats
    
    def get_cached_services(self) -> List[str]:
        """Get list of cached service names"""
        return list(self._cache.keys())


# Pre-configured discovery clients for voice assistant services

class VoiceAssistantDiscovery:
    """
    Pre-configured discovery for voice assistant services.
    """
    
    # Default service ports
    DEFAULT_PORTS = {
        'gateway': 8000,
        'asr': 50051,
        'nlu': 50052,
        'dialog': 50053,
        'tts': 50054,
        'storage': 50055,
        'notification': 50056
    }
    
    @classmethod
    def create_client(
        cls,
        registry: Optional[ServiceRegistry] = None,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    ) -> DiscoveryClient:
        """Create discovery client with voice assistant defaults"""
        config = DiscoveryConfig(
            load_balancing_strategy=strategy,
            cache_ttl_seconds=30,
            refresh_interval_seconds=10
        )
        return DiscoveryClient(registry, config)
    
    @classmethod
    async def discover_asr(cls, client: DiscoveryClient) -> Optional[ServiceEndpoint]:
        """Discover ASR service endpoint"""
        return await client.get_endpoint('asr_service')
    
    @classmethod
    async def discover_nlu(cls, client: DiscoveryClient) -> Optional[ServiceEndpoint]:
        """Discover NLU service endpoint"""
        return await client.get_endpoint('nlu_service')
    
    @classmethod
    async def discover_dialog(cls, client: DiscoveryClient) -> Optional[ServiceEndpoint]:
        """Discover Dialog service endpoint"""
        return await client.get_endpoint('dialog_service')
    
    @classmethod
    async def discover_tts(cls, client: DiscoveryClient) -> Optional[ServiceEndpoint]:
        """Discover TTS service endpoint"""
        return await client.get_endpoint('tts_service')
    
    @classmethod
    async def discover_storage(cls, client: DiscoveryClient) -> Optional[ServiceEndpoint]:
        """Discover Storage service endpoint"""
        return await client.get_endpoint('storage_service')
    
    @classmethod
    def get_default_address(cls, service_name: str, host: str = 'localhost') -> str:
        """Get default address for a service"""
        port = cls.DEFAULT_PORTS.get(service_name, 80)
        return f"{host}:{port}"
