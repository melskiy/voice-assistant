"""
Base classes and registry for Gateway Service views.
Implements the view factory/decorator pattern for clean registration.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from fastapi import APIRouter, FastAPI, Request, HTTPException
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseViewSet')


class ViewRegistry:
    """
    Registry for viewsets.
    Implements the factory pattern for view registration.
    """
    _viewsets: Dict[str, Type['BaseViewSet']] = {}
    _instances: Dict[str, 'BaseViewSet'] = {}

    @classmethod
    def register(cls, name: str, viewset_class: Type[T]) -> Type[T]:
        """
        Register a viewset class.
        
        Args:
            name: Unique identifier for the viewset
            viewset_class: The viewset class to register
            
        Returns:
            The registered viewset class (for decorator use)
        """
        cls._viewsets[name] = viewset_class
        logger.info(f"Registered viewset: {name}")
        return viewset_class

    @classmethod
    def get_viewset(cls, name: str) -> Optional[Type['BaseViewSet']]:
        """Get a registered viewset class by name"""
        return cls._viewsets.get(name)

    @classmethod
    def get_all_viewsets(cls) -> Dict[str, Type['BaseViewSet']]:
        """Get all registered viewset classes"""
        return cls._viewsets.copy()

    @classmethod
    def create_instance(
        cls,
        name: str,
        app: FastAPI,
        prefix: str = "",
        **dependencies: Any
    ) -> Optional['BaseViewSet']:
        """
        Create and initialize a viewset instance.
        
        Args:
            name: Viewset name
            app: FastAPI application instance
            prefix: URL prefix for routes
            **dependencies: Dependencies to inject into the viewset
            
        Returns:
            Initialized viewset instance or None if not found
        """
        viewset_class = cls._viewsets.get(name)
        if not viewset_class:
            logger.error(f"Viewset not found: {name}")
            return None

        instance = viewset_class(app, prefix, **dependencies)
        cls._instances[name] = instance
        return instance

    @classmethod
    def create_all(
        cls,
        app: FastAPI,
        base_prefix: str = "/v1",
        **dependencies: Any
    ) -> List['BaseViewSet']:
        """
        Create and initialize all registered viewsets.
        
        Args:
            app: FastAPI application instance
            base_prefix: Base URL prefix for all routes
            **dependencies: Dependencies to inject into viewsets
            
        Returns:
            List of initialized viewset instances
        """
        instances = []
        for name, viewset_class in cls._viewsets.items():
            try:
                prefix = f"{base_prefix}{viewset_class.router_prefix}"
                instance = cls.create_instance(name, app, prefix, **dependencies)
                if instance:
                    instances.append(instance)
                    logger.info(f"Initialized viewset: {name} with prefix {prefix}")
            except Exception as e:
                logger.error(f"Failed to initialize viewset {name}: {e}")
        return instances

    @classmethod
    def clear(cls) -> None:
        """Clear all registered viewsets and instances"""
        cls._viewsets.clear()
        cls._instances.clear()


def viewset(name: str, prefix: str = "") -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to register a viewset class.
    
    Args:
        name: Unique identifier for the viewset
        prefix: URL prefix for this viewset's routes
        
    Example:
        @viewset("health", "/health")
        class HealthViewSet(BaseViewSet):
            ...
    """
    def decorator(cls: Type[T]) -> Type[T]:
        cls.router_prefix = prefix
        return ViewRegistry.register(name, cls)
    return decorator


class BaseViewSet(ABC):
    """
    Abstract base class for all viewsets.
    
    Provides common functionality for:
    - Router creation and registration
    - Dependency injection
    - Error handling
    - Request context access
    """
    
    router_prefix: str = ""
    tags: List[str] = []
    
    def __init__(
        self,
        app: FastAPI,
        prefix: str = "",
        **dependencies: Any
    ):
        """
        Initialize the viewset.
        
        Args:
            app: FastAPI application instance
            prefix: URL prefix for routes
            **dependencies: Dependencies injected from app state
        """
        self.app = app
        self.prefix = prefix
        self.dependencies = dependencies
        self.router = APIRouter(prefix=prefix, tags=self.tags)
        
        # Register routes
        self._register_routes()
        
        # Include router in app
        app.include_router(self.router)
        
        logger.info(f"ViewSet {self.__class__.__name__} initialized with prefix {prefix}")

    @abstractmethod
    def _register_routes(self) -> None:
        """
        Register all routes for this viewset.
        Must be implemented by subclasses.
        """
        pass

    def get_dependency(self, name: str) -> Any:
        """
        Get a dependency by name.
        
        Args:
            name: Dependency name
            
        Returns:
            The dependency or None if not found
        """
        return self.dependencies.get(name)

    def get_app_state(self, request: Request) -> Any:
        """
        Get application state from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Application state
        """
        return request.app.state

    def get_state_attr(self, request: Request, attr: str) -> Any:
        """
        Get an attribute from application state.
        
        Args:
            request: FastAPI request object
            attr: Attribute name
            
        Returns:
            Attribute value or None if not found
        """
        state = self.get_app_state(request)
        return getattr(state, attr, None) if hasattr(state, attr) else None

    @staticmethod
    def handle_error(message: str, status_code: int = 500, details: Optional[Dict] = None) -> HTTPException:
        """
        Create a standardized error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
            
        Returns:
            HTTPException ready to be raised
        """
        error_detail = {"error": message}
        if details:
            error_detail.update(details)
        return HTTPException(status_code=status_code, detail=error_detail)

    def require_state_attr(self, request: Request, attr: str) -> Any:
        """
        Require an attribute from application state, raise error if not found.
        
        Args:
            request: FastAPI request object
            attr: Attribute name
            
        Returns:
            Attribute value
            
        Raises:
            HTTPException: If attribute is not found
        """
        value = self.get_state_attr(request, attr)
        if value is None:
            raise self.handle_error(
                f"Required service '{attr}' not available",
                status_code=503
            )
        return value