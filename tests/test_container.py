"""
Unit tests for dependency injection container.
"""

import pytest
from rodi import Container

from voice_assistant.interfaces.container import create_container, Config, get_container
from voice_assistant.domain.entities.call_session import CallSession


class TestContainer:
    """Unit tests for DI container configuration"""
    
    def test_create_container(self):
        """Test creating a container with default configuration"""
        container = create_container()
        
        assert isinstance(container, Container)
        
        # Test that Config is registered
        config = container.resolve(Config)
        assert isinstance(config, Config)
        
        # Test configuration values
        assert config.audio_chunk_duration_ms == 200
        assert config.audio_sample_rate == 8000
        assert config.audio_channels == 1
        assert config.max_concurrent_sessions == 100
    
    def test_get_container(self):
        """Test getting container instance"""
        container = get_container()
        assert isinstance(container, Container)
    
    def test_config_environment_variables(self, monkeypatch):
        """Test configuration with environment variables"""
        # Set environment variables
        monkeypatch.setenv("AUDIO_CHUNK_DURATION_MS", "100")
        monkeypatch.setenv("MAX_CONCURRENT_SESSIONS", "50")
        monkeypatch.setenv("ASR_SERVICE_URL", "localhost:60051")
        
        container = create_container()
        config = container.resolve(Config)
        
        assert config.audio_chunk_duration_ms == 100
        assert config.max_concurrent_sessions == 50
        assert config.asr_service_url == "localhost:60051"
    
    def test_call_session_factory(self):
        """Test CallSession factory registration"""
        container = create_container()
        
        # CallSession factory should be registered
        factory = container.resolve("call_session_factory")
        assert callable(factory)
        
        # Test creating a CallSession through the factory
        session = factory("+1234567890", {"test": True})
        assert session.__class__.__name__ == "CallSession"
        assert session.caller_id == "+1234567890"
        assert session.metadata["test"] is True
    
    def test_service_specific_containers(self):
        """Test creating service-specific containers"""
        from voice_assistant.interfaces.container import create_service_container
        
        # Test different service containers
        for service_name in ["asr_service", "nlu_service", "tts_service", "unknown_service"]:
            container = create_service_container(service_name)
            assert isinstance(container, Container)
            
            # Should still have basic configuration
            config = container.resolve(Config)
            assert isinstance(config, Config)