"""
Regex NLU Plugin.

This plugin provides regex-based natural language understanding.

Usage:
    from rodi import Container
    from plugins.nlu_regex import RegexNluPluginRegistration
    
    container = Container()
    config = {"language": "ru", "case_sensitive": False}
    RegexNluPluginRegistration.register(container, config)
    
    # Resolve and use the service
    nlu_service = container.resolve(INluService)
    result = await nlu_service.classify_intent("добавь молоко в список")
"""

from .registration import RegexNluPluginRegistration
from .interfaces import IIntentPattern, IEntityExtractor, IPatternRepository
from .services.pattern_repository import (
    IntentPattern,
    RegexEntityExtractor,
    InMemoryPatternRepository
)
from .services.nlu_service import RegexNluService

__all__ = [
    # Registration
    "RegexNluPluginRegistration",
    # Interfaces
    "IIntentPattern",
    "IEntityExtractor",
    "IPatternRepository",
    # Services
    "IntentPattern",
    "RegexEntityExtractor",
    "InMemoryPatternRepository",
    "RegexNluService",
]
