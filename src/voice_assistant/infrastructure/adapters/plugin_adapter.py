"""
Plugin Adapter - Infrastructure adapter for plugin management.

Offline capability: yes (depends on plugin implementations)
CPU load: ~1% (management overhead)
Model size: N/A
"""
from pathlib import Path
from typing import Any

from ...application.ports.plugin_port import PluginPort
from ...application.ports.asr_port import ASRPort
from ...application.ports.nlu_port import NLUPort
from ...application.ports.tts_port import TTSPort
from ..plugins.plugin_manager import PluginManager


class PluginAdapter(PluginPort):
    """
    Adapter for plugin management using PluginManager.
    
    Implements PluginPort by delegating to the legacy PluginManager.
    Provides a clean interface for the application layer.
    """
    
    def __init__(self, plugins_directory: str | None = None):
        # Use default directory if not specified
        if plugins_directory is None:
            current_file_dir = Path(__file__).parent
            plugins_path = current_file_dir.parent.parent.parent / "plugins"
            plugins_directory = str(plugins_path.resolve())
        
        self._plugin_manager = PluginManager(plugins_directory)
        self._configured_plugins: dict[str, str] = {}
        self._active_plugins: dict[str, Any] = {}
    
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
        try:
            # Discover available plugins
            available_plugins = self._plugin_manager.discover_plugins()
            print(f"Discovered plugins: {available_plugins}")
            
            # Initialize configured plugins
            for plugin_id, config in plugin_configs.items():
                if config.get("enabled", False):
                    try:
                        await self._plugin_manager.load_plugin(plugin_id, config)
                        print(f"Successfully loaded plugin: {plugin_id}")
                    except Exception as e:
                        print(f"Failed to load plugin {plugin_id}: {e}")
                        return False
            
            return True
        except Exception as e:
            print(f"Error initializing plugins: {e}")
            return False
    
    def select_active_plugins(self, plugin_selections: dict[str, str]) -> None:
        """
        Select which plugins to use for each category.
        
        Args:
            plugin_selections: Dictionary mapping categories to plugin IDs
        """
        self._configured_plugins = plugin_selections.copy()
        
        for category, plugin_id in plugin_selections.items():
            try:
                plugin = self._plugin_manager.get_loaded_plugin(plugin_id)
                self._active_plugins[category] = plugin
                print(f"Selected {category} plugin: {plugin_id}")
            except Exception as e:
                print(f"Failed to select {category} plugin {plugin_id}: {e}")
    
    def get_asr_plugin(self) -> ASRPort | None:
        """Get the active ASR plugin."""
        from ..plugins.plugin_interface import ASRPlugin
        plugin = self._active_plugins.get("asr")
        if plugin is not None and isinstance(plugin, ASRPlugin):
            return plugin
        return None
    
    def get_nlu_plugin(self) -> NLUPort | None:
        """Get the active NLU plugin."""
        from ..plugins.plugin_interface import NLUPlugin
        plugin = self._active_plugins.get("nlu")
        if plugin is not None and isinstance(plugin, NLUPlugin):
            return plugin
        return None
    
    def get_tts_plugin(self) -> TTSPort | None:
        """Get the active TTS plugin."""
        from ..plugins.plugin_interface import TTSPlugin
        plugin = self._active_plugins.get("tts")
        if plugin is not None and isinstance(plugin, TTSPlugin):
            return plugin
        return None
    
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup resources."""
        await self._plugin_manager.shutdown_all_plugins()
        self._active_plugins.clear()
    
    def is_available(self, plugin_type: str) -> bool:
        """
        Check if a plugin type is available.
        
        Args:
            plugin_type: Type of plugin (asr, nlu, tts)
            
        Returns:
            True if plugin is available
        """
        if plugin_type == "asr":
            return self.get_asr_plugin() is not None
        elif plugin_type == "nlu":
            return self.get_nlu_plugin() is not None
        elif plugin_type == "tts":
            return self.get_tts_plugin() is not None
        return False
