"""
Application Bootstrap - Initializes all application components.

User goal: Start the voice assistant application.
Success guarantee: All components are initialized and ready.
Side effects: Initializes plugins, repositories, and services.
"""
from typing import Any

from ..application.ports.plugin_port import PluginPort
from ..application.use_cases.process_voice_command import ProcessVoiceCommand
from ..application.use_cases.transcribe_audio import TranscribeAudio
from ..application.use_cases.manage_dialog_state import ManageDialogState
from ..application.handlers.add_shopping_item_handler import AddShoppingItemHandler
from ..application.handlers.create_reminder_handler import CreateReminderHandler
from ..infrastructure.adapters.plugin_adapter import PluginAdapter
from ..infrastructure.external.health_checker import HealthChecker


class Config:
    """Configuration for bootstrap."""
    
    def __init__(
        self,
        plugins_directory: str | None = None,
        plugin_configs: dict[str, dict[str, Any]] | None = None,
        default_plugins: dict[str, str] | None = None
    ):
        self.plugins_directory = plugins_directory
        self.plugin_configs = plugin_configs or {}
        self.default_plugins = default_plugins or {}


class ApplicationBootstrap:
    """
    Bootstrap class for initializing the voice assistant application.
    
    Responsible for:
    - Initializing plugins
    - Setting up repositories
    - Creating use cases
    - Wiring dependencies
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.plugin_port: PluginPort | None = None
        self.health_checker: HealthChecker | None = None
        self.use_cases: dict[str, Any] = {}
        self.handlers: dict[str, Any] = {}
    
    async def initialize(self) -> 'VoiceAssistantApplication':
        """
        Initialize all application components.
        
        Returns:
            Initialized application ready to start
        """
        print("Initializing voice assistant application...")
        
        # Step 1: Initialize plugin adapter
        self.plugin_port = PluginAdapter(self.config.plugins_directory)
        
        # Step 2: Initialize plugins
        enabled_configs = {
            plugin_id: config
            for plugin_id, config in self.config.plugin_configs.items()
            if config.get("enabled", False)
        }
        
        print(f"Initializing plugins: {list(enabled_configs.keys())}")
        success = await self.plugin_port.initialize_plugins(enabled_configs)
        
        if not success:
            raise Exception("Failed to initialize plugins")
        
        # Step 3: Select active plugins
        self.plugin_port.select_active_plugins(self.config.default_plugins)
        
        # Step 4: Initialize health checker
        self.health_checker = HealthChecker(self.plugin_port)
        
        # Step 5: Create use cases (with mock repositories for now)
        # In production, these would be real repositories
        from ..domain.repositories.session_repository import ISessionRepository
        from ..domain.repositories.shopping_repository import IShoppingRepository
        from ..domain.repositories.reminder_repository import IReminderRepository
        
        # Mock repositories - replace with real implementations
        session_repo = self._create_mock_session_repository()
        shopping_repo = self._create_mock_shopping_repository()
        reminder_repo = self._create_mock_reminder_repository()
        
        asr_plugin = self.plugin_port.get_asr_plugin()
        nlu_plugin = self.plugin_port.get_nlu_plugin()
        tts_plugin = self.plugin_port.get_tts_plugin()
        
        if not asr_plugin or not nlu_plugin:
            raise Exception("Required plugins not available")
        
        # Create use cases
        self.use_cases["process_voice_command"] = ProcessVoiceCommand(
            asr_port=asr_plugin,
            nlu_port=nlu_plugin,
            tts_port=tts_plugin,
            session_repo=session_repo
        )
        
        self.use_cases["transcribe_audio"] = TranscribeAudio(asr_port=asr_plugin)
        self.use_cases["manage_dialog_state"] = ManageDialogState(session_repo=session_repo)
        
        # Create handlers
        self.handlers["add_shopping_item"] = AddShoppingItemHandler(
            shopping_repo=shopping_repo,
            session_repo=session_repo
        )
        self.handlers["create_reminder"] = CreateReminderHandler(
            reminder_repo=reminder_repo,
            session_repo=session_repo
        )
        
        print("Voice assistant application initialized successfully!")
        
        return VoiceAssistantApplication(
            bootstrap=self,
            plugin_port=self.plugin_port,
            health_checker=self.health_checker,
            use_cases=self.use_cases,
            handlers=self.handlers
        )
    
    def _create_mock_session_repository(self):
        """Create mock session repository for demonstration."""
        from ..domain.repositories.session_repository import ISessionRepository
        
        class MockSessionRepository(ISessionRepository):
            def __init__(self):
                self._sessions = {}
            
            async def get_by_id(self, session_id):
                return self._sessions.get(session_id)
            
            async def save(self, session):
                self._sessions[session.id] = session
            
            async def update(self, session):
                self._sessions[session.id] = session
            
            async def delete(self, session_id):
                if session_id in self._sessions:
                    del self._sessions[session_id]
        
        return MockSessionRepository()
    
    def _create_mock_shopping_repository(self):
        """Create mock shopping repository for demonstration."""
        from ..domain.repositories.shopping_repository import IShoppingRepository
        
        class MockShoppingRepository(IShoppingRepository):
            def __init__(self):
                self._lists = {}
            
            async def get_by_session(self, session_id):
                return self._lists.get(session_id)
            
            async def save(self, shopping_list):
                self._lists[shopping_list.session_id] = shopping_list
            
            async def update(self, shopping_list):
                self._lists[shopping_list.session_id] = shopping_list
            
            async def delete(self, session_id):
                if session_id in self._lists:
                    del self._lists[session_id]
        
        return MockShoppingRepository()
    
    def _create_mock_reminder_repository(self):
        """Create mock reminder repository for demonstration."""
        from ..domain.repositories.reminder_repository import IReminderRepository
        
        class MockReminderRepository(IReminderRepository):
            def __init__(self):
                self._reminders = {}
            
            async def get_by_session(self, session_id, date_range_start=None, date_range_end=None):
                return [
                    r for r in self._reminders.values()
                    if r.session_id == session_id
                ]
            
            async def save(self, reminder):
                self._reminders[reminder.id] = reminder
            
            async def update(self, reminder):
                self._reminders[reminder.id] = reminder
            
            async def delete(self, reminder_id):
                if reminder_id in self._reminders:
                    del self._reminders[reminder_id]
        
        return MockReminderRepository()


class VoiceAssistantApplication:
    """
    Application facade providing access to all components.
    
    This is the main interface for running the voice assistant.
    """
    
    def __init__(
        self,
        bootstrap: ApplicationBootstrap,
        plugin_port: PluginPort,
        health_checker: HealthChecker,
        use_cases: dict[str, Any],
        handlers: dict[str, Any]
    ):
        self._bootstrap = bootstrap
        self.plugin_port = plugin_port
        self.health_checker = health_checker
        self.use_cases = use_cases
        self.handlers = handlers
        self._running = False
    
    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        return await self.health_checker.check_health()
    
    async def start(self) -> None:
        """Start the application."""
        print("Starting voice assistant application...")
        self._running = True
        
        # Check health before starting
        health = await self.health_check()
        print(f"Health status: {health['status']}")
        
        print("Voice assistant is running. Press Ctrl+C to stop.")
        
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop the application."""
        print("Stopping voice assistant application...")
        self._running = False
        
        # Shutdown plugins
        if self.plugin_port:
            await self.plugin_port.shutdown()
        
        print("Voice assistant application stopped.")
    
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running


import asyncio  # For start method
