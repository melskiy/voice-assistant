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
from ..plugins.plugin_manager import IoC_PluginManager


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

        # Create a container for the plugin manager
        from rodi import Container
        container = Container()

        self._plugin_manager = IoC_PluginManager(container, plugins_directory=plugins_directory)
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
            # Discover and register plugins using IoC_PluginManager
            registered_plugins = self._plugin_manager.discover_and_register_plugins(plugin_configs)
            print(f"Registered plugins: {registered_plugins}")

            return len(registered_plugins) > 0
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
                # For IoC_PluginManager, we need to resolve the plugin from the container
                # This assumes the plugin was registered with a known interface
                from rodi import Container
                # We'll store plugin_id for later resolution when needed
                self._active_plugins[category] = plugin_id
                print(f"Selected {category} plugin: {plugin_id}")
            except Exception as e:
                print(f"Failed to select {category} plugin {plugin_id}: {e}")
    
    def get_asr_plugin(self) -> ASRPort | None:
        """Get the active ASR plugin."""
        from ..plugins.plugin_contracts import IAsrService
        plugin_id = self._active_plugins.get("asr")
        if plugin_id:
            try:
                # Resolve the plugin from the container
                plugin = self._plugin_manager.container.resolve(IAsrService)
                return plugin
            except Exception:
                # If direct resolution fails, try to resolve by plugin_id
                try:
                    # Attempt to resolve by class name or plugin_id
                    plugin = self._plugin_manager.container.resolve(plugin_id)
                    return plugin
                except Exception:
                    return None
        return None

    def get_nlu_plugin(self) -> NLUPort | None:
        """Get the active NLU plugin."""
        from ..plugins.plugin_contracts import INluService
        plugin_id = self._active_plugins.get("nlu")
        if plugin_id:
            try:
                # Resolve the plugin from the container
                plugin = self._plugin_manager.container.resolve(INluService)
                return plugin
            except Exception:
                # If direct resolution fails, try to resolve by plugin_id
                try:
                    # Attempt to resolve by class name or plugin_id
                    plugin = self._plugin_manager.container.resolve(plugin_id)
                    return plugin
                except Exception:
                    return None
        return None

    def get_tts_plugin(self) -> TTSPort | None:
        """Get the active TTS plugin."""
        from ..plugins.plugin_contracts import ITtsService
        plugin_id = self._active_plugins.get("tts")
        if plugin_id:
            try:
                # Resolve the plugin from the container
                plugin = self._plugin_manager.container.resolve(ITtsService)
                return plugin
            except Exception:
                # If direct resolution fails, try to resolve by plugin_id
                try:
                    # Attempt to resolve by class name or plugin_id
                    plugin = self._plugin_manager.container.resolve(plugin_id)
                    return plugin
                except Exception:
                    return None
        return None
    
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup resources."""
        # IoC_PluginManager doesn't have shutdown_all_plugins method
        # For now, just clear the active plugins
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
