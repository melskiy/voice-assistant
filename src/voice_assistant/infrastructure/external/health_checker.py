"""
Health Checker - Infrastructure service for system health monitoring.

Offline capability: yes
CPU load: ~0.1%
Model size: N/A
"""
import asyncio
from typing import Any

from ...application.ports.plugin_port import PluginPort


class HealthChecker:
    """
    Service for checking system health status.
    
    Checks availability of all components and returns health status.
    """
    
    def __init__(self, plugin_port: PluginPort):
        self.plugin_port = plugin_port
    
    async def check_health(self) -> dict[str, Any]:
        """
        Perform health check of all components.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "components": {
                "plugin_service": {
                    "status": "available" if self.plugin_port else "unavailable"
                },
                "asr_plugin": {
                    "status": (
                        "available" 
                        if self.plugin_port.is_available("asr") 
                        else "unavailable"
                    )
                },
                "nlu_plugin": {
                    "status": (
                        "available" 
                        if self.plugin_port.is_available("nlu") 
                        else "unavailable"
                    )
                },
                "tts_plugin": {
                    "status": (
                        "available" 
                        if self.plugin_port.is_available("tts") 
                        else "unavailable"
                    )
                }
            }
        }
        
        # Check if any component is unhealthy
        for component, details in health_status["components"].items():
            if details["status"] == "unavailable":
                health_status["status"] = "degraded"
        
        return health_status
    
    def is_healthy(self) -> bool:
        """
        Quick health check.
        
        Returns:
            True if all critical components are available
        """
        return (
            self.plugin_port.is_available("asr") and
            self.plugin_port.is_available("nlu")
        )
