"""
Tests for AudioStreamManager functionality
"""
import pytest
import asyncio
from uuid import uuid4
import base64
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from voice_assistant.application.services.audio_stream_manager import AudioStreamManager
from voice_assistant.interfaces.container import Config


class TestAudioStreamManager:
    """Test audio stream manager functionality"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        config = Config()
        config.audio_chunk_duration_ms = 200
        config.audio_sample_rate = 8000
        config.audio_channels = 1
        config.asr_service_url = "localhost:50051"
        return config
    
    @pytest.fixture
    def audio_manager(self, config):
        """Create audio stream manager"""
        return AudioStreamManager(config)
    
    def test_initialization(self, audio_manager, config):
        """Test audio manager initialization"""
        assert audio_manager.chunk_duration_ms == config.audio_chunk_duration_ms
        assert audio_manager.sample_rate == config.audio_sample_rate
        assert audio_manager.channels == config.audio_channels
        
        # Check calculated chunk size (200ms at 8kHz, 1 channel, 16-bit = 3200 bytes)
        expected_chunk_size = int((8000 * 200 * 1 * 2) / 1000)
        assert audio_manager.chunk_size_bytes == expected_chunk_size
    
    def test_decode_base64_audio(self, audio_manager):
        """Test base64 audio decoding"""
        # Create test audio data
        test_data = b"test_audio_data"
        encoded_data = base64.b64encode(test_data).decode('utf-8')
        
        decoded = audio_manager.decode_base64_audio(encoded_data)
        assert decoded == test_data
    
    def test_decode_invalid_base64(self, audio_manager):
        """Test invalid base64 handling"""
        with pytest.raises(ValueError, match="Invalid base64 audio data"):
            audio_manager.decode_base64_audio("invalid_base64!")
    
    def test_segment_audio_data(self, audio_manager):
        """Test audio segmentation"""
        session_id = uuid4()
        
        # Create audio data that's exactly 2 chunks worth
        chunk_size = audio_manager.chunk_size_bytes
        audio_data = b'\x00' * (chunk_size * 2)
        
        chunks = audio_manager.segment_audio_data(audio_data, session_id)
        
        assert len(chunks) == 2
        assert all(len(chunk.data) == chunk_size for chunk in chunks)
        assert chunks[0].sequence_number == 0
        assert chunks[1].sequence_number == 1
        assert all(chunk.sample_rate == 8000 for chunk in chunks)
        assert all(chunk.channels == 1 for chunk in chunks)
    
    def test_segment_audio_data_with_padding(self, audio_manager):
        """Test audio segmentation with padding for small chunks"""
        session_id = uuid4()
        
        # Create audio data that's smaller than one chunk
        chunk_size = audio_manager.chunk_size_bytes
        small_audio_data = b'\x01' * (chunk_size // 2)
        
        chunks = audio_manager.segment_audio_data(small_audio_data, session_id)
        
        assert len(chunks) == 1
        assert len(chunks[0].data) == chunk_size  # Should be padded to full size
        assert chunks[0].sequence_number == 0
        # Duration should reflect original data size, not padded size
        expected_duration = len(small_audio_data) / (8000 * 1 * 2)
        assert abs(chunks[0].duration - expected_duration) < 0.001
    
    def test_segment_empty_audio_data(self, audio_manager):
        """Test handling of empty audio data"""
        session_id = uuid4()
        
        chunks = audio_manager.segment_audio_data(b'', session_id)
        
        assert len(chunks) == 0
    
    def test_segment_audio_data_with_partial_end_chunk(self, audio_manager):
        """Test handling of partial chunks at the end"""
        session_id = uuid4()
        
        # Create audio data that's 1.75 chunks (partial end chunk should be padded)
        chunk_size = audio_manager.chunk_size_bytes
        audio_data = b'\x00' * chunk_size + b'\x01' * int(chunk_size * 0.75)
        
        chunks = audio_manager.segment_audio_data(audio_data, session_id)
        
        # Should get 2 complete chunks (second one padded)
        assert len(chunks) == 2
        assert len(chunks[0].data) == chunk_size
        assert len(chunks[1].data) == chunk_size  # Padded
        assert chunks[0].sequence_number == 0
        assert chunks[1].sequence_number == 1
    
    def test_audio_chunk_to_protobuf(self, audio_manager):
        """Test conversion to protobuf format"""
        from voice_assistant.domain.value_objects.audio_chunk import AudioChunk
        
        chunk = AudioChunk.create(
            data=b"test_data",
            sample_rate=8000,
            channels=1,
            sequence_number=5
        )
        
        pb_chunk = audio_manager.audio_chunk_to_protobuf(chunk)
        
        assert pb_chunk.audio_data == chunk.data
        assert pb_chunk.sample_rate == chunk.sample_rate
        assert pb_chunk.channels == chunk.channels
        assert pb_chunk.sequence_number == chunk.sequence_number
        assert pb_chunk.duration_ms == int(chunk.duration * 1000)
    
    def test_get_stream_stats(self, audio_manager):
        """Test stream statistics"""
        stats = audio_manager.get_stream_stats()
        
        assert "active_streams" in stats
        assert "asr_connections" in stats
        assert "chunk_size_bytes" in stats
        assert "chunk_duration_ms" in stats
        assert "sample_rate" in stats
        
        assert stats["active_streams"] == 0  # No active streams initially
        assert stats["asr_connections"] == 0  # No connections initially
        assert stats["chunk_size_bytes"] == audio_manager.chunk_size_bytes
        assert stats["chunk_duration_ms"] == 200
        assert stats["sample_rate"] == 8000
    
    @pytest.mark.asyncio
    async def test_initialize_connections(self, audio_manager):
        """Test connection initialization for all service types"""
        # These will fail in test environment but should not raise exceptions
        asr_result = await audio_manager.initialize_asr_connection("localhost:50051")
        nlu_result = await audio_manager.initialize_nlu_connection("localhost:50052")
        tts_result = await audio_manager.initialize_tts_connection("localhost:50054")
        
        # In test environment, connections will fail but methods should handle gracefully
        assert isinstance(asr_result, bool)
        assert isinstance(nlu_result, bool)
        assert isinstance(tts_result, bool)
    
    def test_get_enhanced_stream_stats(self, audio_manager):
        """Test enhanced stream statistics"""
        stats = audio_manager.get_stream_stats()
        
        expected_keys = [
            "active_streams", "asr_connections", "nlu_connections", "tts_connections",
            "total_connections", "chunk_size_bytes", "chunk_duration_ms", 
            "sample_rate", "channels", "bytes_per_sample"
        ]
        
        for key in expected_keys:
            assert key in stats
        
        assert stats["total_connections"] == 0  # No connections initially
        assert stats["channels"] == 1
        assert stats["bytes_per_sample"] == 2
    
    @pytest.mark.asyncio
    async def test_close_all_connections(self, audio_manager):
        """Test closing all connection types"""
        # Should not raise any errors even with no connections
        await audio_manager.close_connections()
        
        # Verify all connection dictionaries are cleared
        assert len(audio_manager.asr_channels) == 0
        assert len(audio_manager.nlu_channels) == 0
        assert len(audio_manager.tts_channels) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])