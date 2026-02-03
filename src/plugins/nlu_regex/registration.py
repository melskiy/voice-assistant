"""
Regex NLU Plugin Registration.

This module contains ONLY the registration logic for the IoC container.
"""

from typing import Any, Dict
from rodi import Container

from voice_assistant.infrastructure.plugins.plugin_contracts import (
    IPluginRegistration,
    PluginMetadata,
    INluService
)
from .interfaces import IPatternRepository, IEntityExtractor
from .services.pattern_repository import InMemoryPatternRepository, RegexEntityExtractor
from .services.nlu_service import RegexNluService


class RegexNluPluginRegistration(IPluginRegistration):
    """
    Registration class for Regex NLU plugin.
    
    This class is responsible ONLY for registering dependencies in the IoC container.
    """
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            plugin_id="nlu.regex",
            name="Regex NLU",
            version="1.0.0",
            description="Regex-based natural language understanding",
            author="Voice Assistant Team",
            dependencies=[]  # No external dependencies
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            JSON Schema for configuration validation
        """
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "default": "ru",
                    "description": "Language code for patterns (ru, en)"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether pattern matching is case sensitive"
                },
                "default_confidence": {
                    "type": "number",
                    "default": 0.8,
                    "description": "Default confidence score for matches"
                }
            },
            "required": []
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if plugin is available.
        
        Regex NLU has no external dependencies, so it's always available.
        
        Returns:
            Always True
        """
        return True
    
    @classmethod
    def register(cls, container: Container, config: Dict[str, Any]) -> None:
        """
        Register Regex NLU dependencies in the IoC container.
        
        Args:
            container: The IoC container
            config: Plugin configuration dictionary
        """
        # Extract configuration
        language = config.get("language", "ru")
        case_sensitive = config.get("case_sensitive", False)
        default_confidence = config.get("default_confidence", 0.8)
        
        # Register configuration as named instance
        container.add_instance(config, name="nlu_regex_config")
        
        # Register pattern repository as singleton
        def repository_factory(c: Container) -> IPatternRepository:
            return InMemoryPatternRepository(
                language=language,
                case_sensitive=case_sensitive
            )
        
        container.add_singleton(IPatternRepository, repository_factory)
        
        # Register entity extractor as singleton
        def extractor_factory(c: Container) -> IEntityExtractor:
            return RegexEntityExtractor(language=language)
        
        container.add_singleton(IEntityExtractor, extractor_factory)
        
        # Register NLU service as singleton
        def service_factory(c: Container) -> INluService:
            repository = c.resolve(IPatternRepository)
            extractor = c.resolve(IEntityExtractor)
            return RegexNluService(
                pattern_repository=repository,
                entity_extractor=extractor,
                default_confidence=default_confidence
            )
        
        container.add_singleton(INluService, service_factory)
        
        # Store registration info
        metadata = cls.get_metadata()
        container.add_instance(metadata, name=f"metadata.{metadata.plugin_id}")
