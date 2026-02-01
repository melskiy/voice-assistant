"""
Application ports (interfaces) for infrastructure adapters.

Following the Dependency Inversion Principle, these ports define
contracts that infrastructure adapters must implement.
"""

from .asr_port import ASRPort
from .nlu_port import NLUPort
from .tts_port import TTSPort
from .plugin_port import PluginPort

__all__ = [
    'ASRPort',
    'NLUPort',
    'TTSPort',
    'PluginPort',
]
