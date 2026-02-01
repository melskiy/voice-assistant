"""
Plugin service for managing and accessing plugins throughout the application.
This service handles plugin selection, initialization, and provides access to active plugins.
"""
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional, Type

from voice_assistant.infrastructure.plugins import IoC_PluginManager
from voice_assistant.infrastructure.plugins.plugin_interface import Plugin, ASRPlugin, NLUPlugin, TTSPlugin
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.application.dto.intent_dto import IntentDTO
from voice_assistant.domain.value_objects.audio_chunk import AudioChunk


class PluginService:
    """
    Service for managing and using plugins in the voice assistant core.
    Provides methods for selecting and using active plugins for ASR, NLU, and TTS.
    """
    
    def __init__(self, plugins_directory: str = None):
        # Use the directory of this file to calculate the absolute path to plugins
        if plugins_directory is None:
            # Get the directory of the current file (__file__)
            current_file_dir = Path(__file__).parent
            # Navigate to the plugins directory relative to this file
            # Assuming structure: src/voice_assistant/application/services/plugin_service.py
            # And plugins are at: src/plugins
            plugins_path = current_file_dir.parent.parent.parent / "plugins"
            plugins_directory = str(plugins_path.resolve())
        
        self.plugin_manager = IoC_PluginManager(plugins_directory)
        self.configured_plugins: Dict[str, str] = {}  # Maps category to plugin ID
        self.active_plugins: Dict[str, Plugin] = {}  # Maps category to active plugin instance
        
    async def initialize_plugins(self, plugin_configs: Dict[str, Dict[str, Any]]) -> bool:
        """
        Initialize plugins based on configuration.
        
        Args:
            plugin_configs: Dictionary mapping plugin IDs to their configurations
            
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Discover all available plugins
            available_plugins = self.plugin_manager.discover_plugins()
            print(f"Discovered plugins: {available_plugins}")
            
            # Initialize configured plugins
            for plugin_id, config in plugin_configs.items():
                if config.get("enabled", False):
                    try:
                        plugin = await self.plugin_manager.load_plugin(plugin_id, config)
                        print(f"Successfully loaded plugin: {plugin_id}")
                    except Exception as e:
                        print(f"Failed to load plugin {plugin_id}: {e}")
                        return False
                        
            return True
        except Exception as e:
            print(f"Error initializing plugins: {e}")
            return False
    
    def select_active_plugins(self, plugin_selections: Dict[str, str]):
        """
        Select which plugins to use for each category (ASR, NLU, TTS).
        
        Args:
            plugin_selections: Dictionary mapping categories to plugin IDs
                              e.g., {"asr": "asr.vosk", "nlu": "nlu.regex", "tts": "tts.silero"}
        """
        self.configured_plugins = plugin_selections.copy()
        
        # Load the selected plugins as active plugins
        for category, plugin_id in plugin_selections.items():
            try:
                plugin = self.plugin_manager.get_loaded_plugin(plugin_id)
                self.active_plugins[category] = plugin
                print(f"Selected {category} plugin: {plugin_id}")
            except Exception as e:
                print(f"Failed to select {category} plugin {plugin_id}: {e}")
    
    def get_asr_plugin(self) -> Optional[ASRPlugin]:
        """Get the active ASR plugin."""
        plugin = self.active_plugins.get("asr")
        if plugin is not None and isinstance(plugin, ASRPlugin):
            return plugin
        return None
    
    def get_nlu_plugin(self) -> Optional[NLUPlugin]:
        """Get the active NLU plugin."""
        plugin = self.active_plugins.get("nlu")
        if plugin is not None and isinstance(plugin, NLUPlugin):
            return plugin
        return None
    
    def get_tts_plugin(self) -> Optional[TTSPlugin]:
        """Get the active TTS plugin."""
        plugin = self.active_plugins.get("tts")
        if plugin is not None and isinstance(plugin, TTSPlugin):
            return plugin
        return None
    
    async def transcribe_audio(self, audio_chunk: AudioChunk) -> Optional[TranscriptionDTO]:
        """Transcribe audio using the active ASR plugin."""
        asr_plugin = self.get_asr_plugin()
        if asr_plugin is None:
            print("No active ASR plugin available")
            return None
        
        try:
            return await asr_plugin.transcribe(audio_chunk)
        except Exception as e:
            print(f"Error during ASR transcription: {e}")
            return None
    
    async def classify_intent(self, text: str) -> Optional[IntentDTO]:
        """Classify intent using the active NLU plugin."""
        nlu_plugin = self.get_nlu_plugin()
        if nlu_plugin is None:
            print("No active NLU plugin available")
            return None
        
        try:
            return await nlu_plugin.classify_intent(text)
        except Exception as e:
            print(f"Error during NLU classification: {e}")
            return None
    
    async def synthesize_speech(self, text: str) -> Optional[bytes]:
        """Synthesize speech using the active TTS plugin."""
        tts_plugin = self.get_tts_plugin()
        if tts_plugin is None:
            print("No active TTS plugin available")
            return None
        
        try:
            return await tts_plugin.synthesize(text)
        except Exception as e:
            print(f"Error during TTS synthesis: {e}")
            return None
    
    async def start_recognition_session(self, session_id: str):
        """Start a recognition session for the ASR plugin."""
        asr_plugin = self.get_asr_plugin()
        if asr_plugin:
            await asr_plugin.start_recognition_session(session_id)
    
    async def end_recognition_session(self, session_id: str):
        """End a recognition session for the ASR plugin."""
        asr_plugin = self.get_asr_plugin()
        if asr_plugin:
            await asr_plugin.end_recognition_session(session_id)
    
    async def shutdown(self):
        """Shutdown all plugins."""
        await self.plugin_manager.shutdown_all_plugins()