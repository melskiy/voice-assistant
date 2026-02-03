import importlib.util
from pathlib import Path
from typing import Any, Type, Dict, List, Optional
from rodi import Container as RoDIContainer
from ..container.extended_container import ExtendedContainer

from .plugin_contracts import IPluginRegistration, PluginMetadata


class IoC_PluginManager:

    def __init__(self, container: ExtendedContainer = None, plugins_directory: str = "src/plugins"):
        if container is None:
            self.container = ExtendedContainer()
        else:
            self.container = container

        # Convert to absolute path if it's relative
        plugins_path = Path(plugins_directory)
        if not plugins_path.is_absolute():
            # Get the project root (assuming this file is in src/voice_assistant/infrastructure/plugins/)
            current_file_dir = Path(__file__).parent
            project_root = current_file_dir.parent.parent.parent.parent  # ../../../../
            self.plugins_directory = project_root / plugins_directory
        else:
            self.plugins_directory = plugins_path

        self.registered_plugins: Dict[str, Type[IPluginRegistration]] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
    
    def discover_and_register_plugins(
        self,
        plugin_configs: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        Discover available plugins and register them in IoC container.

        Args:
            plugin_configs: Dictionary mapping plugin IDs to their configurations

        Returns:
            List of registered plugin IDs
        """
        registered_plugin_ids = []

        # Check if plugins directory exists
        if not self.plugins_directory.exists():
            print(f"Plugins directory does not exist: {self.plugins_directory}")
            return registered_plugin_ids

        for plugin_dir in self.plugins_directory.iterdir():
            if not plugin_dir.is_dir():
                continue

            # Check for registration.py (new architecture)
            registration_file = plugin_dir / "registration.py"
            if registration_file.exists():
                try:
                    plugin_id = self._register_from_registration_file(
                        plugin_dir, plugin_configs
                    )
                    if plugin_id:
                        registered_plugin_ids.append(plugin_id)
                except Exception as e:
                    print(f"Failed to load plugin from {plugin_dir}: {e}")
                    continue

        return registered_plugin_ids
    
    def _register_from_registration_file(
        self,
        plugin_dir: Path,
        plugin_configs: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """
        Register a plugin from its registration.py file.
        
        Args:
            plugin_dir: Path to plugin directory
            plugin_configs: Plugin configurations
            
        Returns:
            Plugin ID if registered successfully, None otherwise
        """
        # Import the registration module
        spec = importlib.util.spec_from_file_location(
            f"{plugin_dir.name}_registration",
            plugin_dir / "registration.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the registration class
        registration_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type) and
                issubclass(attr, IPluginRegistration) and
                attr is not IPluginRegistration
            ):
                registration_class = attr
                break
        
        if not registration_class:
            print(f"No registration class found in {plugin_dir}")
            return None
        
        # Get plugin metadata
        metadata = registration_class.get_metadata()
        plugin_id = metadata.plugin_id
        
        # Check if plugin is available
        if not registration_class.is_available():
            print(f"Plugin {plugin_id} is not available in current environment")
            return None
        
        # Get plugin configuration
        config = plugin_configs.get(plugin_id, {})
        
        # Check if plugin is enabled (default to True if not specified)
        if not config.get("enabled", True):
            print(f"Plugin {plugin_id} is disabled")
            return None
        
        # Register plugin in IoC container
        try:
            registration_class.register(self.container, config)
            
            # Store plugin info
            self.registered_plugins[plugin_id] = registration_class
            self.plugin_configs[plugin_id] = config
            self.plugin_metadata[plugin_id] = metadata
            
            print(f"Registered plugin: {plugin_id} ({metadata.name})")
            return plugin_id
            
        except Exception as e:
            print(f"Failed to register plugin {plugin_id}: {e}")
            return None
    
    def get_plugin_class(self, plugin_id: str) -> Type[IPluginRegistration]:
        """
        Get a plugin registration class by ID.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin registration class
            
        Raises:
            ValueError: If plugin not found
        """
        if plugin_id not in self.registered_plugins:
            raise ValueError(f"Plugin {plugin_id} not found")
        
        return self.registered_plugins[plugin_id]
    
    def get_plugin_metadata(self, plugin_id: str) -> PluginMetadata:
        """
        Get plugin metadata by ID.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin metadata
            
        Raises:
            ValueError: If plugin not found
        """
        if plugin_id not in self.plugin_metadata:
            raise ValueError(f"Plugin {plugin_id} not found")
        
        return self.plugin_metadata[plugin_id]
    
    def list_registered_plugins(self) -> List[str]:
        """
        List all registered plugin IDs.
        
        Returns:
            List of plugin IDs
        """
        return list(self.registered_plugins.keys())
    
    def get_plugins_by_type(self, plugin_type: str) -> List[str]:
        """
        Get list of registered plugins of specific type.
        
        Args:
            plugin_type: Plugin type prefix (e.g., "asr", "nlu", "tts")
            
        Returns:
            List of plugin IDs
        """
        return [
            plugin_id for plugin_id in self.registered_plugins.keys()
            if plugin_id.startswith(f"{plugin_type}.")
        ]
    
    def reload_plugin(
        self,
        plugin_id: str,
        new_config: Dict[str, Any]
    ) -> None:
        """
        Reload a plugin with new configuration.

        Args:
            plugin_id: Plugin identifier
            new_config: New configuration dictionary

        Raises:
            ValueError: If plugin not found
        """
        if plugin_id not in self.registered_plugins:
            raise ValueError(f"Plugin {plugin_id} not found")

        registration_class = self.registered_plugins[plugin_id]

        # Re-register with new config
        registration_class.register(self.container, new_config)
        self.plugin_configs[plugin_id] = new_config

        print(f"Reloaded plugin: {plugin_id}")

    def get_asr_plugin(self):
        """Get the registered ASR plugin from the container."""
        from .plugin_contracts import IAsrService
        try:
            return self.container.resolve(IAsrService)
        except (KeyError, ValueError):
            return None

    def get_nlu_plugin(self):
        """Get the registered NLU plugin from the container."""
        from .plugin_contracts import INluService
        try:
            return self.container.resolve(INluService)
        except (KeyError, ValueError):
            return None

    def get_tts_plugin(self):
        """Get the registered TTS plugin from the container."""
        from .plugin_contracts import ITtsService
        try:
            return self.container.resolve(ITtsService)
        except (KeyError, ValueError):
            return None


class PluginDiscovery:
    """
    Utility class for discovering available plugins.
    
    This class can be used to list available plugins without registering them.
    """
    
    @staticmethod
    def list_available_plugins(plugins_directory: str = "src/plugins") -> List[Dict[str, Any]]:
        """
        List all available plugins without registering them.
        
        Args:
            plugins_directory: Path to plugins directory
            
        Returns:
            List of plugin information dictionaries
        """
        plugins_dir = Path(plugins_directory)
        available_plugins = []
        
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            registration_file = plugin_dir / "registration.py"
            if registration_file.exists():
                try:
                    # Import the registration module
                    spec = importlib.util.spec_from_file_location(
                        f"{plugin_dir.name}_registration",
                        registration_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find the registration class
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type) and
                            issubclass(attr, IPluginRegistration) and
                            attr is not IPluginRegistration
                        ):
                            metadata = attr.get_metadata()
                            available_plugins.append({
                                "id": metadata.plugin_id,
                                "name": metadata.name,
                                "version": metadata.version,
                                "description": metadata.description,
                                "author": metadata.author,
                                "dependencies": metadata.dependencies,
                                "available": attr.is_available(),
                                "config_schema": attr.get_config_schema()
                            })
                            break
                            
                except Exception as e:
                    print(f"Failed to inspect plugin {plugin_dir}: {e}")
                    continue
        
        return available_plugins
