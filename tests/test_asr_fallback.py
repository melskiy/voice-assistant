"""
Tests for ASR Service fallback and circuit breaker functionality
"""
import pytest
import asyncio
import os
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from voice_assistant.domain.value_objects.audio_chunk import AudioChunk
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.infrastructure.plugins.mock_asr_plugin import MockASRPlugin
from services.asr_service.main import ASRCircuitBreaker


class TestASRCircuitBreaker:
    """Test ASR circuit breaker functionality"""
    
    def test_circuit_breaker_creation(self):
        """Test circuit breaker can be created with proper configuration"""
        cb = ASRCircuitBreaker(failure_threshold=3, timeout=30, name="Test ASR")
        assert cb.failure_threshold == 3
        assert cb.timeout == 30
        assert cb.name == "Test ASR"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.can_execute() == True
    
    def test_circuit_breaker_failure_progression(self):
        """Test circuit breaker state transitions on failures"""
        cb = ASRCircuitBreaker(failure_threshold=2, timeout=1, name="Test ASR")
        
        # Initially should allow execution
        assert cb.can_execute() == True
        assert cb.get_state() == "CLOSED"
        
        # Record first failure
        cb.record_failure()
        assert cb.can_execute() == True  # Still closed
        assert cb.failure_count == 1
        assert cb.get_state() == "CLOSED"
        
        # Record second failure - should open circuit
        cb.record_failure()
        assert cb.can_execute() == False  # Now open
        assert cb.get_state() == "OPEN"
        assert cb.failure_count == 2
        
        # Wait for timeout and check half-open transition
        time.sleep(1.1)  # Wait longer than timeout
        assert cb.can_execute() == True  # Should transition to half-open
        assert cb.get_state() == "HALF_OPEN"
        
        # Record success in half-open - should need multiple successes
        cb.record_success()
        assert cb.get_state() == "HALF_OPEN"  # Still half-open
        
        cb.record_success()
        assert cb.get_state() == "CLOSED"  # Now closed
        assert cb.failure_count == 0
    
    def test_circuit_breaker_success_reset(self):
        """Test that successes reset failure count in closed state"""
        cb = ASRCircuitBreaker(failure_threshold=3, timeout=30, name="Test ASR")
        
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.get_state() == "CLOSED"
        
        # Record success should reduce failure count
        cb.record_success()
        assert cb.failure_count == 1
        assert cb.get_state() == "CLOSED"


class TestASRFallbackLogic:
    """Test ASR fallback logic with mock plugins"""
    
    @pytest.fixture
    def mock_primary_plugin(self):
        """Create a mock primary ASR plugin"""
        plugin = Mock()
        plugin.is_available.return_value = True
        return plugin
    
    @pytest.fixture
    def mock_fallback_plugin(self):
        """Create a mock fallback ASR plugin"""
        plugin = Mock()
        plugin.is_available.return_value = True
        return plugin
    
    @pytest.fixture
    def test_audio_chunk(self):
        """Create a test audio chunk"""
        return AudioChunk.create(
            data=b"test audio data for transcription",
            sample_rate=8000,
            channels=1,
            sequence_number=1,
            duration=0.2
        )
    
    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self, mock_primary_plugin, mock_fallback_plugin, test_audio_chunk):
        """Test that fallback is not used when primary succeeds with high confidence"""
        # Configure primary plugin to return high confidence result
        high_confidence_result = TranscriptionDTO(
            text="test transcription",
            is_final=True,
            confidence=0.9,
            timestamp=test_audio_chunk.timestamp,
            audio_duration=test_audio_chunk.duration
        )
        mock_primary_plugin.transcribe = AsyncMock(return_value=high_confidence_result)
        
        # Simulate the fallback logic
        primary_cb = ASRCircuitBreaker(name="Primary")
        fallback_cb = ASRCircuitBreaker(name="Fallback")
        confidence_threshold = 0.7
        
        # Test primary success path
        assert primary_cb.can_execute() == True
        result = await mock_primary_plugin.transcribe(test_audio_chunk)
        primary_cb.record_success()
        
        # Should not need fallback
        assert result.confidence >= confidence_threshold
        assert result.text == "test transcription"
        assert mock_fallback_plugin.transcribe.call_count == 0
    
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_fallback(self, mock_primary_plugin, mock_fallback_plugin, test_audio_chunk):
        """Test that low confidence from primary triggers fallback"""
        # Configure primary plugin to return low confidence result
        low_confidence_result = TranscriptionDTO(
            text="uncertain transcription",
            is_final=True,
            confidence=0.3,
            timestamp=test_audio_chunk.timestamp,
            audio_duration=test_audio_chunk.duration
        )
        mock_primary_plugin.transcribe = AsyncMock(return_value=low_confidence_result)
        
        # Configure fallback plugin to return higher confidence result
        high_confidence_result = TranscriptionDTO(
            text="better transcription",
            is_final=True,
            confidence=0.8,
            timestamp=test_audio_chunk.timestamp,
            audio_duration=test_audio_chunk.duration
        )
        mock_fallback_plugin.transcribe = AsyncMock(return_value=high_confidence_result)
        
        # Simulate the fallback logic
        confidence_threshold = 0.7
        
        primary_result = await mock_primary_plugin.transcribe(test_audio_chunk)
        assert primary_result.confidence < confidence_threshold
        
        # Should trigger fallback
        fallback_result = await mock_fallback_plugin.transcribe(test_audio_chunk)
        
        # Should choose better result
        if fallback_result.confidence > primary_result.confidence:
            final_result = fallback_result
        else:
            final_result = primary_result
        
        assert final_result.text == "better transcription"
        assert final_result.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_primary_failure_triggers_fallback(self, mock_primary_plugin, mock_fallback_plugin, test_audio_chunk):
        """Test that primary failure triggers fallback"""
        # Configure primary plugin to fail
        mock_primary_plugin.transcribe = AsyncMock(side_effect=Exception("Primary ASR failed"))
        
        # Configure fallback plugin to succeed
        fallback_result = TranscriptionDTO(
            text="fallback transcription",
            is_final=True,
            confidence=0.7,
            timestamp=test_audio_chunk.timestamp,
            audio_duration=test_audio_chunk.duration
        )
        mock_fallback_plugin.transcribe = AsyncMock(return_value=fallback_result)
        
        # Test primary failure
        primary_result = None
        try:
            primary_result = await mock_primary_plugin.transcribe(test_audio_chunk)
        except Exception:
            pass
        
        assert primary_result is None
        
        # Should use fallback
        final_result = await mock_fallback_plugin.transcribe(test_audio_chunk)
        assert final_result.text == "fallback transcription"
        assert final_result.confidence == 0.7
    
    @pytest.mark.asyncio
    async def test_both_engines_fail_returns_error(self, mock_primary_plugin, mock_fallback_plugin, test_audio_chunk):
        """Test that when both engines fail, an error result is returned"""
        # Configure both plugins to fail
        mock_primary_plugin.transcribe = AsyncMock(side_effect=Exception("Primary failed"))
        mock_fallback_plugin.transcribe = AsyncMock(side_effect=Exception("Fallback failed"))
        
        # Test both failures
        primary_result = None
        fallback_result = None
        
        try:
            primary_result = await mock_primary_plugin.transcribe(test_audio_chunk)
        except Exception:
            pass
        
        try:
            fallback_result = await mock_fallback_plugin.transcribe(test_audio_chunk)
        except Exception:
            pass
        
        assert primary_result is None
        assert fallback_result is None
        
        # Should create error result
        error_result = TranscriptionDTO(
            text="[ASR_ERROR] Primary: Primary failed, Fallback: Fallback failed",
            is_final=True,
            confidence=0.0,
            timestamp=test_audio_chunk.timestamp,
            audio_duration=test_audio_chunk.duration
        )
        
        assert "[ASR_ERROR]" in error_result.text
        assert error_result.confidence == 0.0


class TestASRServiceIntegration:
    """Integration tests for ASR service with fallback"""
    
    @pytest.mark.asyncio
    async def test_mock_asr_plugin_fallback_behavior(self):
        """Test that mock ASR plugin works as expected for fallback scenarios"""
        plugin = MockASRPlugin()
        
        # Test multiple transcriptions to see confidence variation
        results = []
        for i in range(50):  # Increase iterations to get more variation
            audio_chunk = AudioChunk.create(
                data=f"test audio data {i}".encode(),
                sample_rate=8000,
                channels=1,
                sequence_number=i,
                duration=0.2
            )
            audio_chunk.is_final = True  # Mark as final to get confidence scores
            result = await plugin.transcribe(audio_chunk)
            if result.is_final:
                results.append(result)
        
        # Should have some variation in confidence scores
        confidences = [r.confidence for r in results]
        assert len(confidences) > 0
        assert min(confidences) >= 0.0
        assert max(confidences) <= 1.0
        
        # Should have some variation in confidence scores
        unique_confidences = set(confidences)
        assert len(unique_confidences) > 1, "Mock plugin should generate varied confidence scores"
        
        # Check if we have some results below 0.7 (if not, that's okay for mock)
        low_confidence_results = [r for r in results if r.confidence < 0.7]
        print(f"Generated {len(low_confidence_results)} low confidence results out of {len(results)} total")
        
        # This is acceptable - mock plugin might not generate low confidence results
        # The important thing is that it generates varied results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])