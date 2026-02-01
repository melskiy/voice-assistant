"""
Service Registry Implementation

Business concept: Central registry for service instances with health status
tracking and automatic cleanup of unhealthy instances.

Constraints:
- Thread-safe operations
- TTL-based instance expiration
- Support for multiple instances per service
- Metadata storage for service discovery
"""

import threading
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service instance status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """
    Represents a registered service instance.
    
    Attributes:
        instance_id: Unique instance identifier
        service_name: Service type (e.g., 'asr', 'nlu', 'gateway')
        host: Service host address
        port: Service port
        status: Current health status
        metadata: Additional service metadata
        registered_at: Registration timestamp
        last_heartbeat: Last heartbeat timestamp
        ttl_seconds: Time-to-live in seconds
    """
    instance_id: str
    service_name: str
    host: str
    port: int
    status: ServiceStatus = ServiceStatus.STARTING
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 30
    
    def is_expired(self) -> bool:
        """Check if instance has expired (no heartbeat within TTL)"""
        expiry_time = self.last_heartbeat + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time
    
    def get_address(self) -> str:
        """Get service address as host:port"""
        return f"{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'instance_id': self.instance_id,
            'service_name': self.service_name,
            'host': self.host,
            'port': self.port,
            'status': self.status.value,
            'metadata': self.metadata,
            'registered_at': self.registered_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'ttl_seconds': self.ttl_seconds,
            'is_expired': self.is_expired(),
            'address': self.get_address()
        }


@dataclass
class ServiceInfo:
    """Aggregated information about a service type"""
    service_name: str
    instances: List[ServiceInstance]
    healthy_count: int
    unhealthy_count: int
    
    def get_healthy_instances(self) -> List[ServiceInstance]:
        """Get only healthy instances"""
        return [
            inst for inst in self.instances 
            if inst.status == ServiceStatus.HEALTHY and not inst.is_expired()
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'service_name': self.service_name,
            'total_instances': len(self.instances),
            'healthy_count': self.healthy_count,
            'unhealthy_count': self.unhealthy_count,
            'instances': [inst.to_dict() for inst in self.instances]
        }


class ServiceRegistry:
    """
    In-memory service registry with TTL-based expiration.
    
    Thread-safe implementation supporting:
    - Service registration/deregistration
    - Heartbeat updates
    - Health status updates
    - Automatic cleanup of expired instances
    """
    
    def __init__(self, cleanup_interval_seconds: int = 60):
        """
        Initialize service registry.
        
        Args:
            cleanup_interval_seconds: Interval for cleaning up expired instances
        """
        self._instances: Dict[str, ServiceInstance] = {}
        self._service_index: Dict[str, List[str]] = {}  # service_name -> instance_ids
        self._lock = threading.RLock()
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_timer: Optional[threading.Timer] = None
        
        # Statistics
        self._stats = {
            'registrations': 0,
            'deregistrations': 0,
            'heartbeats': 0,
            'cleanups': 0,
            'expired_removed': 0
        }
        
        logger.info("Service registry initialized")
    
    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = 30
    ) -> ServiceInstance:
        """
        Register a new service instance.
        
        Args:
            service_name: Service type identifier
            host: Service host address
            port: Service port
            metadata: Optional service metadata
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            Registered service instance
        """
        with self._lock:
            instance_id = str(uuid.uuid4())
            instance = ServiceInstance(
                instance_id=instance_id,
                service_name=service_name,
                host=host,
                port=port,
                status=ServiceStatus.STARTING,
                metadata=metadata or {},
                ttl_seconds=ttl_seconds
            )
            
            self._instances[instance_id] = instance
            
            # Update service index
            if service_name not in self._service_index:
                self._service_index[service_name] = []
            self._service_index[service_name].append(instance_id)
            
            self._stats['registrations'] += 1
            
            logger.info(
                f"Registered {service_name} instance {instance_id} at {host}:{port}"
            )
            
            return instance
    
    def deregister(self, instance_id: str) -> bool:
        """
        Deregister a service instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            True if deregistered, False if not found
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            # Remove from instances
            del self._instances[instance_id]
            
            # Remove from service index
            service_name = instance.service_name
            if service_name in self._service_index:
                self._service_index[service_name] = [
                    id for id in self._service_index[service_name] 
                    if id != instance_id
                ]
                if not self._service_index[service_name]:
                    del self._service_index[service_name]
            
            self._stats['deregistrations'] += 1
            
            logger.info(f"Deregistered {service_name} instance {instance_id}")
            return True
    
    def heartbeat(self, instance_id: str, status: Optional[ServiceStatus] = None) -> bool:
        """
        Update instance heartbeat.
        
        Args:
            instance_id: Instance identifier
            status: Optional new status
            
        Returns:
            True if updated, False if not found
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            instance.last_heartbeat = datetime.utcnow()
            
            if status:
                instance.status = status
            
            self._stats['heartbeats'] += 1
            
            logger.debug(f"Heartbeat received for {instance.service_name} instance {instance_id}")
            return True
    
    def update_status(self, instance_id: str, status: ServiceStatus) -> bool:
        """
        Update instance health status.
        
        Args:
            instance_id: Instance identifier
            status: New health status
            
        Returns:
            True if updated, False if not found
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            old_status = instance.status
            instance.status = status
            instance.last_heartbeat = datetime.utcnow()
            
            if old_status != status:
                logger.info(
                    f"Status changed for {instance.service_name} instance {instance_id}: "
                    f"{old_status.value} -> {status.value}"
                )
            
            return True
    
    def update_metadata(self, instance_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update instance metadata.
        
        Args:
            instance_id: Instance identifier
            metadata: Metadata to update (merged with existing)
            
        Returns:
            True if updated, False if not found
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            instance.metadata.update(metadata)
            return True
    
    def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        """Get instance by ID"""
        with self._lock:
            return self._instances.get(instance_id)
    
    def get_service(self, service_name: str) -> ServiceInfo:
        """
        Get information about a service type.
        
        Args:
            service_name: Service type identifier
            
        Returns:
            Service information
        """
        with self._lock:
            instance_ids = self._service_index.get(service_name, [])
            instances = [
                self._instances[id] for id in instance_ids 
                if id in self._instances
            ]
            
            healthy = sum(1 for inst in instances if inst.status == ServiceStatus.HEALTHY)
            unhealthy = len(instances) - healthy
            
            return ServiceInfo(
                service_name=service_name,
                instances=instances,
                healthy_count=healthy,
                unhealthy_count=unhealthy
            )
    
    def get_healthy_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """
        Get a healthy instance for a service (round-robin selection).
        
        Args:
            service_name: Service type identifier
            
        Returns:
            Healthy service instance or None
        """
        with self._lock:
            service_info = self.get_service(service_name)
            healthy = service_info.get_healthy_instances()
            
            if not healthy:
                return None
            
            # Simple round-robin: select instance with oldest heartbeat
            return min(healthy, key=lambda x: x.last_heartbeat)
    
    def get_all_services(self) -> List[str]:
        """Get list of all registered service names"""
        with self._lock:
            return list(self._service_index.keys())
    
    def get_all_instances(self) -> List[ServiceInstance]:
        """Get all registered instances"""
        with self._lock:
            return list(self._instances.values())
    
    def cleanup_expired(self) -> int:
        """
        Remove expired instances.
        
        Returns:
            Number of instances removed
        """
        with self._lock:
            expired_ids = [
                id for id, inst in self._instances.items() 
                if inst.is_expired()
            ]
            
            for id in expired_ids:
                self.deregister(id)
            
            self._stats['cleanups'] += 1
            self._stats['expired_removed'] += len(expired_ids)
            
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired instances")
            
            return len(expired_ids)
    
    def start_cleanup_task(self):
        """Start periodic cleanup task"""
        def cleanup_task():
            self.cleanup_expired()
            self._cleanup_timer = threading.Timer(self._cleanup_interval, cleanup_task)
            self._cleanup_timer.daemon = True
            self._cleanup_timer.start()
        
        if self._cleanup_timer is None:
            cleanup_task()
            logger.info(f"Started cleanup task (interval: {self._cleanup_interval}s)")
    
    def stop_cleanup_task(self):
        """Stop periodic cleanup task"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None
            logger.info("Stopped cleanup task")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._lock:
            stats = self._stats.copy()
            stats['total_instances'] = len(self._instances)
            stats['total_services'] = len(self._service_index)
            return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary"""
        with self._lock:
            return {
                'services': {
                    name: self.get_service(name).to_dict()
                    for name in self._service_index.keys()
                },
                'stats': self.get_stats()
            }


# Singleton registry instance
_registry_instance: Optional[ServiceRegistry] = None
_registry_lock = threading.Lock()


def get_service_registry() -> ServiceRegistry:
    """Get global service registry instance"""
    global _registry_instance
    
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = ServiceRegistry()
        return _registry_instance
