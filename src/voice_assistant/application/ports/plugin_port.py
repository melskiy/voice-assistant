"""
Plugin Port - Interface for plugin management.

User goal: Manage plugin lifecycle and access plugin capabilities.
Success guarantee: Plugins are initialized and available for use.
Side effects: Plugin initialization and shutdown.
"""
from typing import Any, Protocol

from .asr_port import ASRPort
from .nlu_port import NLUPort
from .tts_port import TTSPort


class PluginPort(Protocol):
    """
    Port interface for plugin management.
    
    Infrastructure adapters must implement this interface to provide
    plugin discovery, initialization, and access.
    """
    
    async def initialize_plugins(
        self, 
        plugin_configs: dict[str, dict[str, Any]]
    ) -> bool:
        """
        Initialize plugins based on configuration.
        
        Args:
            plugin_configs: Dictionary mapping plugin IDs to configurations
            
        Returns:
            True if initialization was successful
        """
        ...
    
    def select_active_plugins(self, plugin_selections: dict[str, str]) -> None:
        """
        Select which plugins to use for each category.
        
        Args:
            plugin_selections: Dictionary mapping categories to plugin IDs
                              e.g., {"asr": "asr.vosk", "nlu": "nlu.regex"}
        """
        ...
    
    def get_asr_plugin(self) -> ASRPort | None:
        """Get the active ASR plugin."""
        ...
    
    def get_nlu_plugin(self) -> NLUPort | None:
        """Get the active NLU plugin."""
        ...
    
    def get_tts_plugin(self) -> TTSPort | None:
        """Get the active TTS plugin."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup resources."""
        ...
    
    def is_available(self, plugin_type: str) -> bool:
        """
        Check if a plugin type is available.
        
        Args:
            plugin_type: Type of plugin (asr, nlu, tts)
            
        Returns:
            True if plugin is available
        """
        ...
