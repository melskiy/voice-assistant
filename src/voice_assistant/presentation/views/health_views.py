"""
Health check views for Gateway Service.
"""
import asyncio
from typing import Any, Dict

from fastapi import Request

from .base import BaseViewSet, viewset
from ..schemas import HealthResponse


@viewset("health", "")
class HealthViewSet(BaseViewSet):
    """
    ViewSet for health check endpoints.
    Provides service health status and basic monitoring.
    """
    
    tags = ["Health"]
    
    def _register_routes(self) -> None:
        """Register health check routes"""
        self.router.add_api_route(
            "/health",
            self.health_check,
            methods=["GET"],
            response_model=HealthResponse,
            summary="Health check",
            description="Check if the gateway service is healthy",
        )
        
        self.router.add_api_route(
            "/ready",
            self.readiness_check,
            methods=["GET"],
            response_model=HealthResponse,
            summary="Readiness check",
            description="Check if the service is ready to accept requests",
        )
        
        self.router.add_api_route(
            "/live",
            self.liveness_check,
            methods=["GET"],
            response_model=HealthResponse,
            summary="Liveness check",
            description="Check if the service is alive",
        )

    async def health_check(self, request: Request) -> HealthResponse:
        """
        Comprehensive health check including dependencies.
        
        Returns:
            HealthResponse with service status and version info
        """
        # Check critical dependencies
        dependencies_status = await self._check_dependencies(request)
        
        overall_status = "healthy" if all(dependencies_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            service="gateway",
            timestamp=asyncio.get_running_loop().time(),
            version="1.0.0",
            uptime=self._get_uptime(),
        )

    async def readiness_check(self, request: Request) -> HealthResponse:
        """
        Check if service is ready to accept traffic.
        
        Returns:
            HealthResponse indicating readiness
        """
        # Check if required services are initialized
        # Note: Plugins (ASR/NLU/TTS) are loaded by their respective microservices,
        # not by the Gateway Service. Gateway only needs Redis and gRPC connections.
        session_cache = self.get_state_attr(request, "session_cache")
        audio_manager = self.get_state_attr(request, "audio_stream_manager")

        is_ready = session_cache is not None and audio_manager is not None
        
        return HealthResponse(
            status="ready" if is_ready else "not_ready",
            service="gateway",
            timestamp=asyncio.get_running_loop().time(),
        )

    async def liveness_check(self, request: Request) -> HealthResponse:
        """
        Simple liveness check.
        
        Returns:
            HealthResponse indicating service is alive
        """
        return HealthResponse(
            status="alive",
            service="gateway",
            timestamp=asyncio.get_running_loop().time(),
        )

    async def _check_dependencies(self, request: Request) -> Dict[str, bool]:
        """
        Check status of all dependencies.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary of dependency names and their status
        """
        status = {}
        
        # Check Redis connection
        redis_client = self.get_state_attr(request, "redis_client")
        if redis_client:
            try:
                await redis_client.ping()
                status["redis"] = True
            except Exception:
                status["redis"] = False
        else:
            status["redis"] = False
        
        # Check audio stream manager (gRPC connections to ASR/NLU/TTS services)
        audio_manager = self.get_state_attr(request, "audio_stream_manager")
        status["audio_stream_manager"] = audio_manager is not None
        
        return status

    def _get_uptime(self) -> float:
        """
        Get service uptime in seconds.
        
        Returns:
            Uptime in seconds (placeholder - would track actual start time)
        """
        # In a real implementation, this would track the actual service start time
        # For now, return 0 as we don't have access to the start time
        return 0.0