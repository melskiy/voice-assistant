"""
Plugin infrastructure for the voice assistant.

This module provides the core infrastructure for plugin management,
including interfaces, contracts, and the plugin manager.
"""

from .plugin_contracts import (
    # Registration
    IPluginRegistration,
    PluginMetadata,
    # Service Interfaces
    IAsrService,
    INluService,
    ITtsService,
    IStorageService,
    IMessagingService,
    # Result Types
    TranscriptionResult,
    IntentResult,
    # Base Classes
    BaseService,
    BaseAsrService,
    BaseNluService,
    BaseTtsService,
    BaseStorageService,
    BaseMessagingService,
)
from .plugin_manager import IoC_PluginManager, PluginDiscovery

__all__ = [
    # Registration
    "IPluginRegistration",
    "PluginMetadata",
    # Service Interfaces
    "IAsrService",
    "INluService",
    "ITtsService",
    "IStorageService",
    "IMessagingService",
    # Result Types
    "TranscriptionResult",
    "IntentResult",
    # Base Classes
    "BaseService",
    "BaseAsrService",
    "BaseNluService",
    "BaseTtsService",
    "BaseStorageService",
    "BaseMessagingService",
    # Manager
    "IoC_PluginManager",
    "PluginDiscovery",
]
