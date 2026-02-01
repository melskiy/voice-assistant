"""
Tests for ASR Service implementation
"""
import pytest
import asyncio
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from voice_assistant.domain.value_objects.audio_chunk import AudioChunk
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.infrastructure.plugins.mock_asr_plugin import MockASRPlugin


class TestASRService:
    """Test ASR Service functionality"""
    
    def test_mock_asr_plugin_creation(self):
        """Test that mock ASR plugin can be created"""
        plugin = MockASRPlugin()
        assert plugin.get_id() == "asr.mock"
        assert plugin.is_available() == True
    
    @pytest.mark.asyncio
    async def test_mock_asr_transcription(self):
        """Test mock ASR plugin transcription"""
        plugin = MockASRPlugin()
        
        # Create test audio chunk
        audio_chunk = AudioChunk.create(
            data=b"test audio data",
            sample_rate=8000,
            channels=1,
            sequence_number=1
        )
        
        # Test transcription
        result = await plugin.transcribe(audio_chunk)
        
        assert result is not None
        assert hasattr(result, 'text')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'is_final')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'audio_duration')
        assert isinstance(result.text, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.is_final, bool)
        assert result.timestamp == audio_chunk.timestamp
        assert result.audio_duration == audio_chunk.duration
    
    @pytest.mark.asyncio
    async def test_mock_asr_session_management(self):
        """Test ASR plugin session management"""
        plugin = MockASRPlugin()
        session_id = "test_session_123"
        
        # Test session start
        await plugin.start_recognition_session(session_id)
        assert session_id in plugin.active_sessions
        
        # Test session end
        await plugin.end_recognition_session(session_id)
        assert session_id not in plugin.active_sessions
    
    @pytest.mark.asyncio
    async def test_mock_asr_partial_and_final_results(self):
        """Test that mock ASR generates both partial and final results"""
        plugin = MockASRPlugin()
        
        results = []
        for i in range(10):
            audio_chunk = AudioChunk.create(
                data=f"test audio data {i}".encode(),
                sample_rate=8000,
                channels=1,
                sequence_number=i,
                duration=0.2
            )
            result = await plugin.transcribe(audio_chunk)
            results.append(result)
        
        # Should have mix of partial and final results
        partial_results = [r for r in results if not r.is_final]
        final_results = [r for r in results if r.is_final]
        
        assert len(partial_results) > 0, "Should generate some partial results"
        assert len(final_results) > 0, "Should generate some final results"
        
        # Final results should have confidence > 0
        for result in final_results:
            assert result.confidence > 0.0
        
        # Partial results should have confidence = 0
        for result in partial_results:
            assert result.confidence == 0.0


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_creation(self):
        """Test circuit breaker can be created"""
        # Import directly from the plugin file
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'plugins', 'asr-whisper-cpp'))
        from plugin import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3, timeout=30)
        assert cb.failure_threshold == 3
        assert cb.timeout == 30
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_failure_handling(self):
        """Test circuit breaker failure handling"""
        # Import directly from the plugin file
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'plugins', 'asr-whisper-cpp'))
        from plugin import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=2, timeout=30)
        
        # Initially should allow execution
        assert cb.can_execute() == True
        
        # Record failures
        cb.record_failure()
        assert cb.can_execute() == True  # Still closed
        assert cb.failure_count == 1
        
        cb.record_failure()
        assert cb.can_execute() == False  # Now open
        assert cb.state == "OPEN"
        
        # Record success should reset
        cb.record_success()
        assert cb.can_execute() == True
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])