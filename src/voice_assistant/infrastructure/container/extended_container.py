"""
Extended DI Container that supports named instances in addition to standard RoDI functionality.
"""

from typing import Any, Dict, Type, Union, Callable
from rodi import Container as RoDIContainer


class ExtendedContainer:
    """
    Extended DI Container that wraps RoDI and adds support for named instances.
    """
    
    def __init__(self):
        self._container = RoDIContainer()
        self._named_instances: Dict[str, Any] = {}
        
    def add_instance(self, instance: Any, name: str = None):
        """
        Add an instance to the container.
        
        Args:
            instance: The instance to register
            name: Optional name for the instance (for named registration)
        """
        if name is not None:
            # Store as named instance
            self._named_instances[name] = instance
        else:
            # Register as type if it's a class/type
            instance_type = type(instance) if not isinstance(instance, type) else instance
            self._container.add_instance(instance_type, instance)
            
    def add_singleton(self, service_type: Type, factory: Union[Callable, Type]):
        """
        Add a singleton to the container.
        
        Args:
            service_type: The type to register
            factory: Factory function or class to create the instance
        """
        self._container.add_singleton(service_type, factory)
        
    def add_transient(self, service_type: Type, factory: Callable):
        """
        Add a transient service to the container.
        
        Args:
            service_type: The type to register
            factory: Factory function to create new instances
        """
        self._container.add_transient(service_type, factory)
        
    def resolve(self, service_type: Type = None, name: str = None):
        """
        Resolve a service from the container.

        Args:
            service_type: The type to resolve (optional if name is provided)
            name: Optional name for named instances

        Returns:
            Resolved instance
        """
        if name is not None:
            # Try to resolve from named instances first
            if name in self._named_instances:
                return self._named_instances[name]
            # If not found, try to resolve from RoDI container with a special convention
            # This is a workaround for resolving named instances
            # We'll try to find it by looking for a stored named instance
            raise KeyError(f"Named instance '{name}' not found")

        # Resolve from standard RoDI container
        if service_type is not None:
            try:
                return self._container.resolve(service_type)
            except Exception:
                # If resolution fails, it might be because the type wasn't registered
                # Return None to match the expected behavior
                raise

        raise ValueError("Either service_type or name must be provided")
        
    def resolve_by_name(self, name: str):
        """
        Resolve a service by its name.
        
        Args:
            name: Name of the instance to resolve
            
        Returns:
            Resolved instance
        """
        if name in self._named_instances:
            return self._named_instances[name]
        raise KeyError(f"Named instance '{name}' not found")
        
    @property
    def container(self):
        """Access to the underlying RoDI container."""
        return self._container