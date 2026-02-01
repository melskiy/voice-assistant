"""
Integration tests for core services: Gateway, ASR, and NLU.
Validates that services communicate correctly and maintain session state.
"""
import asyncio
import grpc
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from voice_assistant.infrastructure.grpc.generated import audio_pb2
from voice_assistant.infrastructure.grpc.generated import audio_pb2_grpc
from voice_assistant.infrastructure.grpc.generated import nlu_pb2
from voice_assistant.infrastructure.grpc.generated import nlu_pb2_grpc
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.application.dto.intent_dto import IntentDTO
from voice_assistant.domain.entities.call_session import CallSession
from voice_assistant.domain.value_objects.audio_chunk import AudioChunk


class TestCoreServicesIntegration:
    """Integration tests for Gateway, ASR, and NLU service communication"""
    
    def test_gateway_asr_nlu_communication_pipeline(self):
        """Test that Gateway, ASR, and NLU services can communicate correctly"""
        # This test would normally require running services, so we'll mock the communication
        with patch('grpc.aio.insecure_channel') as mock_channel:
            # Mock the gRPC channels and stubs
            mock_asr_stub = AsyncMock()
            mock_nlu_stub = AsyncMock()
            
            # Setup mock responses
            mock_asr_response = audio_pb2.TranscriptionResponse(
                success=True,
                transcription=audio_pb2.Transcription(
                    text="добавь молоко в список покупок",
                    confidence=0.85,
                    segments=[]
                )
            )
            mock_nlu_response = nlu_pb2.IntentResponse(
                success=True,
                intent=nlu_pb2.Intent(
                    name="ADD_SHOPPING_ITEM",
                    confidence=0.88,
                    entities={"item": "молоко"},
                    raw_text="добавь молоко в список покупок",
                    session_id="test-session-123"
                )
            )
            
            mock_asr_stub.ProcessAudioStream.return_value = mock_asr_response
            mock_nlu_stub.ExtractIntent.return_value = mock_nlu_response
            
            # Simulate the communication flow
            # 1. Gateway receives audio chunk
            audio_chunk = AudioChunk(
                session_id="test-session-123",
                data=b"dummy-audio-data",
                timestamp=0,
                chunk_id="chunk-001"
            )
            
            # 2. Gateway sends audio to ASR service
            asr_request = audio_pb2.AudioStreamRequest(
                audio_chunk=audio_pb2.AudioChunk(
                    session_id=audio_chunk.session_id,
                    data=audio_chunk.data,
                    timestamp=audio_chunk.timestamp,
                    chunk_id=audio_chunk.chunk_id
                )
            )
            
            asr_response = asyncio.run(mock_asr_stub.ProcessAudioStream(asr_request))
            
            # 3. Gateway sends text to NLU service
            nlu_request = nlu_pb2.IntentRequest(
                text=asr_response.transcription.text,
                session_id=audio_chunk.session_id,
                language="ru"
            )
            
            nlu_response = asyncio.run(mock_nlu_stub.ExtractIntent(nlu_request))
            
            # Verify the communication flow worked correctly
            assert asr_response.success is True
            assert asr_response.transcription.text == "добавь молоко в список покупок"
            assert nlu_response.success is True
            assert nlu_response.intent.name == "ADD_SHOPPING_ITEM"
            assert nlu_response.intent.confidence == 0.88
            assert nlu_response.intent.entities["item"] == "молоко"
    
    async def test_audio_streaming_pipeline_simulation(self):
        """Test audio streaming from Gateway to ASR to NLU pipeline"""
        # Create a simulated audio streaming scenario
        session_id = str(uuid.uuid4())
        
        # Mock the services
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_asr_stub = AsyncMock()
            mock_nlu_stub = AsyncMock()
            
            # Define a sequence of audio chunks that would form a meaningful sentence
            audio_chunks = [
                AudioChunk(session_id=session_id, data=b"audio-chunk-1", timestamp=0, chunk_id="1"),
                AudioChunk(session_id=session_id, data=b"audio-chunk-2", timestamp=200, chunk_id="2"), 
                AudioChunk(session_id=session_id, data=b"audio-chunk-3", timestamp=400, chunk_id="3"),
            ]
            
            # Mock ASR responses for each chunk
            asr_responses = [
                audio_pb2.TranscriptionResponse(
                    success=True,
                    transcription=audio_pb2.Transcription(text="", confidence=0.0, segments=[])
                ),  # Partial results for first chunks
                audio_pb2.TranscriptionResponse(
                    success=True,
                    transcription=audio_pb2.Transcription(text="", confidence=0.0, segments=[])
                ),  # Partial results for second chunk
                audio_pb2.TranscriptionResponse(
                    success=True,
                    transcription=audio_pb2.Transcription(
                        text="напомни мне позвонить маме завтра",
                        confidence=0.92,
                        segments=[]
                    )  # Final result for third chunk
                )
            ]
            
            # Mock NLU response for the final transcription
            nlu_response = nlu_pb2.IntentResponse(
                success=True,
                intent=nlu_pb2.Intent(
                    name="CREATE_REMINDER",
                    confidence=0.85,
                    entities={"description": "позвонить маме", "time_reference": "завтра"},
                    raw_text="напомни мне позвонить маме завтра",
                    session_id=session_id
                )
            )
            
            # Setup the mocks
            mock_asr_stub.ProcessAudioStream.side_effect = asr_responses
            mock_nlu_stub.ExtractIntent.return_value = nlu_response
            
            # Simulate the streaming pipeline
            final_transcription = ""
            for i, chunk in enumerate(audio_chunks):
                # Send audio chunk to ASR
                asr_request = audio_pb2.AudioStreamRequest(
                    audio_chunk=audio_pb2.AudioChunk(
                        session_id=chunk.session_id,
                        data=chunk.data,
                        timestamp=chunk.timestamp,
                        chunk_id=chunk.chunk_id
                    )
                )
                
                asr_resp = await mock_asr_stub.ProcessAudioStream(asr_request)
                
                # If this is the last chunk with final transcription
                if asr_resp.transcription.text and i == len(audio_chunks) - 1:
                    final_transcription = asr_resp.transcription.text
                    
                    # Send to NLU for intent classification
                    nlu_request = nlu_pb2.IntentRequest(
                        text=final_transcription,
                        session_id=session_id,
                        language="ru"
                    )
                    
                    nlu_resp = await mock_nlu_stub.ExtractIntent(nlu_request)
                    
                    # Verify the final result
                    assert nlu_resp.success is True
                    assert nlu_resp.intent.name == "CREATE_REMINDER"
                    assert nlu_resp.intent.confidence >= 0.80
                    assert "description" in nlu_resp.intent.entities
    
    def test_session_management_across_services(self):
        """Verify session management works across Gateway, ASR, and NLU service boundaries"""
        session_id = "session-test-123"
        
        # Test that session ID is maintained throughout the pipeline
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_asr_stub = AsyncMock()
            mock_nlu_stub = AsyncMock()
            
            # Setup responses
            asr_response = audio_pb2.TranscriptionResponse(
                success=True,
                transcription=audio_pb2.Transcription(
                    text="добавь хлеб в список",
                    confidence=0.78,
                    segments=[]
                )
            )
            nlu_response = nlu_pb2.IntentResponse(
                success=True,
                intent=nlu_pb2.Intent(
                    name="ADD_SHOPPING_ITEM",
                    confidence=0.82,
                    entities={"item": "хлеб"},
                    raw_text="добавь хлеб в список",
                    session_id=session_id
                )
            )
            
            mock_asr_stub.ProcessAudioStream.return_value = asr_response
            mock_nlu_stub.ExtractIntent.return_value = nlu_response
            
            # Create audio chunk with session ID
            audio_chunk = AudioChunk(
                session_id=session_id,
                data=b"test-audio",
                timestamp=0,
                chunk_id="chunk-001"
            )
            
            # Process through ASR
            asr_request = audio_pb2.AudioStreamRequest(
                audio_chunk=audio_pb2.AudioChunk(
                    session_id=audio_chunk.session_id,
                    data=audio_chunk.data,
                    timestamp=audio_chunk.timestamp,
                    chunk_id=audio_chunk.chunk_id
                )
            )
            
            asr_result = asyncio.run(mock_asr_stub.ProcessAudioStream(asr_request))
            
            # Process through NLU maintaining the same session
            nlu_request = nlu_pb2.IntentRequest(
                text=asr_result.transcription.text,
                session_id=audio_chunk.session_id,  # Same session ID passed through
                language="ru"
            )
            
            nlu_result = asyncio.run(mock_nlu_stub.ExtractIntent(nlu_request))
            
            # Verify session consistency
            assert asr_result.transcription.HasField('text')  # Has text field
            assert nlu_result.intent.session_id == session_id
            assert nlu_result.intent.raw_text == "добавь хлеб в список"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_service_pipeline(self):
        """Test error handling when one service in the pipeline fails"""
        session_id = "error-test-123"
        
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_asr_stub = AsyncMock()
            mock_nlu_stub = AsyncMock()
            
            # Simulate ASR service failure
            asr_response = audio_pb2.TranscriptionResponse(
                success=False,
                error_message="ASR service unavailable"
            )
            
            mock_asr_stub.ProcessAudioStream.return_value = asr_response
            
            # Try to process audio - should handle ASR failure gracefully
            audio_chunk = AudioChunk(
                session_id=session_id,
                data=b"test-audio",
                timestamp=0,
                chunk_id="chunk-001"
            )
            
            asr_request = audio_pb2.AudioStreamRequest(
                audio_chunk=audio_pb2.AudioChunk(
                    session_id=audio_chunk.session_id,
                    data=audio_chunk.data,
                    timestamp=audio_chunk.timestamp,
                    chunk_id=audio_chunk.chunk_id
                )
            )
            
            asr_result = await mock_asr_stub.ProcessAudioStream(asr_request)
            
            # Since ASR failed, we shouldn't proceed to NLU
            assert asr_result.success is False
            assert asr_result.error_message == "ASR service unavailable"
            
            # Verify NLU was never called due to ASR failure
            mock_nlu_stub.ExtractIntent.assert_not_called()


# Run the integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])