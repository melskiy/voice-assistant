"""
Service-specific containers for Voice Assistant.

Each service gets its own container with only the necessary dependencies
and plugins relevant to that service, following the principle of separation
of concerns and reducing coupling between services.
"""

from typing import Any, Dict, Optional
from rodi import Container
import os

from voice_assistant.interfaces.container import Config as AppConfig
from voice_assistant.infrastructure.plugins.plugin_manager import IoC_PluginManager
from voice_assistant.application.use_cases.tts_use_cases import SynthesizeSpeechUseCase, GetAvailableVoicesUseCase
from voice_assistant.application.use_cases.nlu_use_cases import ExtractIntentUseCase, ProcessConfidenceUseCase
from voice_assistant.application.use_cases.asr_use_cases import TranscribeAudioUseCase, ManageASRSessionUseCase
from voice_assistant.application.use_cases.dialog_use_cases import ProcessIntentUseCase, HandleConfirmationUseCase, GetDialogStateUseCase, ResetDialogUseCase
from voice_assistant.domain.services.text_normalizer import RussianTextNormalizer
from voice_assistant.infrastructure.resilience.circuit_breaker import CircuitBreaker
from voice_assistant.infrastructure.persistence.in_memory_dialog_session_repository import InMemoryDialogSessionRepository


class ASRServiceContainer:
    """
    Dependency Injection Container for ASR Service.

    Contains only dependencies needed by the ASR service:
    - ASR plugins
    - Audio processing utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register ASR-specific plugins
        self._register_asr_plugins()

    def _register_asr_plugins(self):
        """Register ASR-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for ASR plugins only
            asr_plugin_configs = {k: v for k, v in plugin_configs.items()
                                  if v.get('type') == 'asr' or 'asr' in k.lower()}

            if asr_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(asr_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for ASR service")

    def create_transcribe_use_case(self, primary_asr, confidence_threshold: float = 0.7):
        """Create TranscribeAudioUseCase with dependencies from container."""
        # Create circuit breakers
        primary_circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv("PRIMARY_ASR_FAILURE_THRESHOLD", "3")),
            timeout=int(os.getenv("PRIMARY_ASR_TIMEOUT", "30")),
            name="Primary ASR"
        )

        fallback_circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv("FALLBACK_ASR_FAILURE_THRESHOLD", "3")),
            timeout=int(os.getenv("FALLBACK_ASR_TIMEOUT", "30")),
            name="Fallback ASR"
        )

        # Create and return use case
        return TranscribeAudioUseCase(
            primary_asr=primary_asr,
            fallback_asr=None,  # Would come from caller if available
            primary_circuit_breaker=primary_circuit_breaker,
            fallback_circuit_breaker=fallback_circuit_breaker,
            confidence_threshold=confidence_threshold
        )

    def create_manage_session_use_case(self, primary_asr, fallback_asr=None):
        """Create ManageASRSessionUseCase with dependencies from container."""
        return ManageASRSessionUseCase(
            primary_asr=primary_asr,
            fallback_asr=fallback_asr
        )

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


class NLUServiceContainer:
    """
    Dependency Injection Container for NLU Service.

    Contains only dependencies needed by the NLU service:
    - NLU plugins
    - Intent processing utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register NLU-specific plugins
        self._register_nlu_plugins()

    def _register_nlu_plugins(self):
        """Register NLU-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for NLU plugins only
            nlu_plugin_configs = {k: v for k, v in plugin_configs.items()
                                  if v.get('type') == 'nlu' or 'nlu' in k.lower()}

            if nlu_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(nlu_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for NLU service")

    def create_extract_intent_use_case(self, nlu_port, confidence_threshold: float = 0.7):
        """Create ExtractIntentUseCase with dependencies from container."""
        return ExtractIntentUseCase(
            nlu_port=nlu_port,
            confidence_threshold=confidence_threshold
        )

    def create_process_confidence_use_case(self):
        """Create ProcessConfidenceUseCase with default configuration."""
        return ProcessConfidenceUseCase(
            high_threshold=0.8,
            medium_threshold=0.6,
            low_threshold=0.4
        )

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


class TTSServiceContainer:
    """
    Dependency Injection Container for TTS Service.

    Contains only dependencies needed by the TTS service:
    - TTS plugins
    - Audio synthesis utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register TTS-specific plugins
        self._register_tts_plugins()

    def _register_tts_plugins(self):
        """Register TTS-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for TTS plugins only
            tts_plugin_configs = {k: v for k, v in plugin_configs.items()
                                  if v.get('type') == 'tts' or 'tts' in k.lower()}

            if tts_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(tts_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for TTS service")

    def create_synthesize_speech_use_case(self, tts_port):
        """Create SynthesizeSpeechUseCase with dependencies from container."""
        text_normalizer = RussianTextNormalizer()

        return SynthesizeSpeechUseCase(
            tts_port=tts_port,
            text_normalizer=text_normalizer
        )

    def create_get_available_voices_use_case(self):
        """Create GetAvailableVoicesUseCase."""
        return GetAvailableVoicesUseCase()

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


class DialogServiceContainer:
    """
    Dependency Injection Container for Dialog Service.

    Contains only dependencies needed by the Dialog service:
    - Dialog plugins
    - State management utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register Dialog-specific plugins
        self._register_dialog_plugins()

    def _register_dialog_plugins(self):
        """Register Dialog-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for dialog-related plugins
            dialog_plugin_configs = {k: v for k, v in plugin_configs.items()
                                     if v.get('type') in ['dialog', 'state']}

            if dialog_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(dialog_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for Dialog service")

    def create_process_intent_use_case(self, error_recovery_service=None):
        """Create ProcessIntentUseCase with dependencies from container."""
        # Using in-memory repository for now - in real app this would come from container
        session_repo = InMemoryDialogSessionRepository()

        return ProcessIntentUseCase(
            session_repo=session_repo,
            error_recovery_service=error_recovery_service
        )

    def create_handle_confirmation_use_case(self):
        """Create HandleConfirmationUseCase with dependencies from container."""
        session_repo = InMemoryDialogSessionRepository()

        return HandleConfirmationUseCase(session_repo)

    def create_get_dialog_state_use_case(self):
        """Create GetDialogStateUseCase with dependencies from container."""
        session_repo = InMemoryDialogSessionRepository()

        return GetDialogStateUseCase(session_repo)

    def create_reset_dialog_use_case(self):
        """Create ResetDialogUseCase with dependencies from container."""
        session_repo = InMemoryDialogSessionRepository()

        return ResetDialogUseCase(session_repo)

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


class GatewayServiceContainer:
    """
    Dependency Injection Container for Gateway Service.

    Contains only dependencies needed by the Gateway service:
    - Gateway plugins
    - API management utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register Gateway-specific plugins
        self._register_gateway_plugins()

    def _register_gateway_plugins(self):
        """Register Gateway-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for gateway-related plugins
            gateway_plugin_configs = {k: v for k, v in plugin_configs.items()
                                      if v.get('type') in ['gateway', 'freeswitch']}

            if gateway_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(gateway_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for Gateway service")

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


class NotificationServiceContainer:
    """
    Dependency Injection Container for Notification Service.

    Contains only dependencies needed by the Notification service:
    - Messaging plugins
    - Notification utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register Notification-specific plugins
        self._register_notification_plugins()

    def _register_notification_plugins(self):
        """Register Notification-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for notification-related plugins
            notification_plugin_configs = {k: v for k, v in plugin_configs.items()
                                           if v.get('type') in ['messaging', 'notification']}

            if notification_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(notification_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for Notification service")

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


class StorageServiceContainer:
    """
    Dependency Injection Container for Storage Service.

    Contains only dependencies needed by the Storage service:
    - Storage plugins
    - Database utilities
    - Related repositories and services
    """

    def __init__(self):
        self.container = Container()
        self.app_config = AppConfig()

        # Register configuration
        self.container.add_instance(AppConfig, self.app_config)

        # Initialize plugin manager
        self.plugin_manager = IoC_PluginManager(self.container)
        self.container.add_instance(IoC_PluginManager, self.plugin_manager)

        # Register Storage-specific plugins
        self._register_storage_plugins()

    def _register_storage_plugins(self):
        """Register Storage-specific plugins."""
        try:
            from plugins.config import get_enabled_plugin_configs
            plugin_configs = get_enabled_plugin_configs()

            # Filter for storage-related plugins
            storage_plugin_configs = {k: v for k, v in plugin_configs.items()
                                      if v.get('type') in ['storage', 'database', 'cache']}

            if storage_plugin_configs:
                self.plugin_manager.discover_and_register_plugins(storage_plugin_configs)
        except ImportError:
            print("Plugin configuration not available for Storage service")

    def get_container(self):
        """Get the underlying RoDI container."""
        return self.container

    def resolve(self, service_type: type, name: Optional[str] = None):
        """Resolve a service from the container."""
        return self.container.resolve(service_type, name)


def create_asr_service_container() -> ASRServiceContainer:
    """Factory function to create ASR service container."""
    return ASRServiceContainer()


def create_nlu_service_container() -> NLUServiceContainer:
    """Factory function to create NLU service container."""
    return NLUServiceContainer()


def create_tts_service_container() -> TTSServiceContainer:
    """Factory function to create TTS service container."""
    return TTSServiceContainer()


def create_dialog_service_container() -> DialogServiceContainer:
    """Factory function to create Dialog service container."""
    return DialogServiceContainer()


def create_gateway_service_container() -> GatewayServiceContainer:
    """Factory function to create Gateway service container."""
    return GatewayServiceContainer()


def create_notification_service_container() -> NotificationServiceContainer:
    """Factory function to create Notification service container."""
    return NotificationServiceContainer()


def create_storage_service_container() -> StorageServiceContainer:
    """Factory function to create Storage service container."""
    return StorageServiceContainer()