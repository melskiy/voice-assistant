from typing import Dict, Type, List, Any
from .plugin_interface import Plugin, PluginType


class PluginRegistry:
    """Registry for managing plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, Type[Plugin]] = {}
        self.plugin_instances: Dict[str, Plugin] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_plugin(self, plugin_class: Type[Plugin]):
        """Register a plugin class"""
        plugin_id = plugin_class.get_id()
        self.plugins[plugin_id] = plugin_class
    
    async def initialize_plugin(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Initialize a plugin with configuration"""
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin {plugin_id} not registered")
        
        plugin_class = self.plugins[plugin_id]
        instance = plugin_class()
        
        if await instance.initialize(config):
            self.plugin_instances[plugin_id] = instance
            self.plugin_configs[plugin_id] = config
            return True
        
        return False
    
    def get_plugin(self, plugin_id: str) -> Plugin:
        """Get initialized plugin instance"""
        return self.plugin_instances.get(plugin_id)
    
    def get_available_plugins_by_type(self, plugin_type: PluginType) -> List[str]:
        """Get list of available plugins of specific type"""
        available = []
        for plugin_id, plugin_class in self.plugins.items():
            if plugin_type.value in plugin_id:
                available.append(plugin_id)
        return available