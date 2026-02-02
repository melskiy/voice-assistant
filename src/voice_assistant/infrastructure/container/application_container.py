"""
Application Container for Voice Assistant Services.

This module provides a centralized dependency injection container
that can be used across all services in the voice assistant system.
Following DDD principles, it manages the lifecycle of all dependencies.
"""

from typing import Any, Dict, Optional, Type, Union
from rodi import Container, Scope
import os
import logging
from grpc import Channel, insecure_channel, secure_channel
from grpc.aio import Channel as AsyncChannel, secure_channel as async_secure_channel, insecure_channel as async_insecure_channel

from voice_assistant.infrastructure.plugins.plugin_manager import IoC_PluginManager
from voice_assistant.interfaces.container import Config as AppConfig


class ApplicationContainer:
    """
    Centralized Dependency Injection Container for Voice Assistant Services.
    
    This container manages all dependencies for the voice assistant services,
    including plugins, repositories, services, and external connections.
    """
    
    def __init__(self, service_name: Optional[str] = None):
        self.container = Container()
        self.service_name = service_name
        self.app_config = AppConfig()
        
        # Initialize the container with common dependencies
        self._register_common_dependencies()
        self._register_service_specific_dependencies()
        
    def _register_common_dependencies(self):
        """Register dependencies common to all services."""
        # Configuration
        self.container.add_instance(AppConfig, self.app_config)
        
        # Plugin manager
        plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, plugin_manager)
        
        # Register gRPC channels for inter-service communication
        self._register_grpc_channels()
        
    def _register_service_specific_dependencies(self):
        """Register dependencies specific to the current service."""
        if self.service_name:
            if self.service_name == "asr_service":
                self._register_asr_service_dependencies()
            elif self.service_name == "nlu_service":
                self._register_nlu_service_dependencies()
            elif self.service_name == "tts_service":
                self._register_tts_service_dependencies()
            elif self.service_name == "dialog_service":
                self._register_dialog_service_dependencies()
            elif self.service_name == "gateway_service":
                self._register_gateway_service_dependencies()
            elif self.service_name == "notification_service":
                self._register_notification_service_dependencies()
            elif self.service_name == "storage_service":
                self._register_storage_service_dependencies()
                
    def _register_grpc_channels(self):
        """Register gRPC channels for inter-service communication."""
        # Register channels for other services
        asr_channel = insecure_channel(self.app_config.asr_service_url)
        nlu_channel = insecure_channel(self.app_config.nlu_service_url)
        dialog_channel = insecure_channel(self.app_config.dialog_service_url)
        tts_channel = insecure_channel(self.app_config.tts_service_url)
        
        self.container.add_instance(Channel, asr_channel, "asr_channel")
        self.container.add_instance(Channel, nlu_channel, "nlu_channel")
        self.container.add_instance(Channel, dialog_channel, "dialog_channel")
        self.container.add_instance(Channel, tts_channel, "tts_channel")
        
    def _register_asr_service_dependencies(self):
        """Register ASR service specific dependencies."""
        # Load ASR plugin
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for ASR plugins only
            asr_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                  if v.get('type') == 'asr' or 'asr' in k.lower()}
            
            if asr_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(asr_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for ASR service")
            
    def _register_nlu_service_dependencies(self):
        """Register NLU service specific dependencies."""
        # Load NLU plugin
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for NLU plugins only
            nlu_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                  if v.get('type') == 'nlu' or 'nlu' in k.lower()}
            
            if nlu_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(nlu_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for NLU service")
            
    def _register_tts_service_dependencies(self):
        """Register TTS service specific dependencies."""
        # Load TTS plugin
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for TTS plugins only
            tts_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                  if v.get('type') == 'tts' or 'tts' in k.lower()}
            
            if tts_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(tts_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for TTS service")
            
    def _register_dialog_service_dependencies(self):
        """Register Dialog service specific dependencies."""
        # Load dialog-related plugins
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for dialog-related plugins
            dialog_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                     if v.get('type') in ['dialog', 'state']}
            
            if dialog_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(dialog_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for Dialog service")
            
    def _register_gateway_service_dependencies(self):
        """Register Gateway service specific dependencies."""
        # Load gateway-related plugins
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for gateway-related plugins
            gateway_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                      if v.get('type') in ['gateway', 'freeswitch']}
            
            if gateway_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(gateway_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for Gateway service")
            
    def _register_notification_service_dependencies(self):
        """Register Notification service specific dependencies."""
        # Load notification-related plugins
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for notification-related plugins
            notification_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                           if v.get('type') in ['messaging', 'notification']}
            
            if notification_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(notification_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for Notification service")
            
    def _register_storage_service_dependencies(self):
        """Register Storage service specific dependencies."""
        # Load storage-related plugins
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()
            
            # Filter for storage-related plugins
            storage_plugin_configs = {k: v for k, v in plugin_configs.items() 
                                      if v.get('type') in ['storage', 'database', 'cache']}
            
            if storage_plugin_configs:
                plugin_manager = self.container.resolve(IoC_PluginManager)
                plugin_manager.discover_and_register_plugins(storage_plugin_configs)
        except ImportError:
            logging.warning("Plugin configuration not available for Storage service")
    
    def register_singleton(self, service_type: Type, implementation: Any):
        """Register a singleton service."""
        self.container.add_singleton(service_type, implementation)
        
    def register_transient(self, service_type: Type, implementation: Any):
        """Register a transient service."""
        self.container.add_transient(service_type, implementation)
        
    def register_scoped(self, service_type: Type, implementation: Any):
        """Register a scoped service."""
        self.container.add_scoped(service_type, implementation)
        
    def resolve(self, service_type: Type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)
        
    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container


def create_application_container(service_name: Optional[str] = None) -> ApplicationContainer:
    """
    Factory function to create an application container.
    
    Args:
        service_name: Name of the service to configure (optional)
        
    Returns:
        Configured ApplicationContainer instance
    """
    return ApplicationContainer(service_name)


def get_service_instance(service_type: Type, service_name: Optional[str] = None):
    """
    Helper function to get a service instance from the container.
    
    Args:
        service_type: Type of service to resolve
        service_name: Name of the service to configure (optional)
        
    Returns:
        Resolved service instance
    """
    container = create_application_container(service_name)
    return container.resolve(service_type)