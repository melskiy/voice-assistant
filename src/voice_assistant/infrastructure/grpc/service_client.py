import grpc
from typing import Dict, Any, Optional
from voice_assistant.application.dto.transcription_dto import TranscriptionDTO
from voice_assistant.application.dto.intent_dto import IntentDTO


class GRPCServiceClient:
    """gRPC client for service-to-service communication"""
    
    def __init__(self, asr_service_url: str, nlu_service_url: str, tts_service_url: str):
        self.asr_service_url = asr_service_url
        self.nlu_service_url = nlu_service_url
        self.tts_service_url = tts_service_url
        
        # Channels for reuse
        self._asr_channel = None
        self._nlu_channel = None
        self._tts_channel = None
    
    async def get_asr_channel(self):
        if self._asr_channel is None or self._asr_channel._state.value != grpc.ChannelConnectivity.READY:
            from voice_assistant.proto import audio_service_pb2_grpc
            self._asr_channel = grpc.aio.insecure_channel(
                self.asr_service_url,
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                ]
            )
        return self._asr_channel
    
    async def get_nlu_channel(self):
        if self._nlu_channel is None or self._nlu_channel._state.value != grpc.ChannelConnectivity.READY:
            from voice_assistant.proto import nlu_service_pb2_grpc
            self._nlu_channel = grpc.aio.insecure_channel(
                self.nlu_service_url,
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                ]
            )
        return self._nlu_channel
    
    async def get_tts_channel(self):
        if self._tts_channel is None or self._tts_channel._state.value != grpc.ChannelConnectivity.READY:
            from voice_assistant.proto import tts_service_pb2_grpc
            self._tts_channel = grpc.aio.insecure_channel(
                self.tts_service_url,
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                ]
            )
        return self._tts_channel
    
    async def transcribe_audio(self, audio_data: bytes, sample_rate: int = 8000) -> TranscriptionDTO:
        """Transcribe audio using gRPC"""
        try:
            from voice_assistant.proto import audio_service_pb2
            from voice_assistant.proto import audio_service_pb2_grpc
            
            channel = await self.get_asr_channel()
            stub = audio_service_pb2_grpc.AudioProcessingServiceStub(channel)
            
            request = audio_service_pb2.AudioChunk(
                session_id="temp_session",
                chunk_id="temp_chunk",
                audio_data=audio_data,
                sample_rate=sample_rate,
                channels=1,
                timestamp=0,
                sequence_number=1,
                is_final=True
            )
            
            response = await stub.Transcribe(request)
            
            return TranscriptionDTO(
                text=response.text,
                confidence=response.confidence,
                is_final=response.is_final,
                timestamp=None,  # Would be handled differently in real implementation
                audio_duration=0.0  # Would be calculated differently
            )
        except grpc.aio.AioRpcError as e:
            raise Exception(f"gRPC ASR call failed: {e.details()}")
    
    async def classify_intent(self, text: str) -> IntentDTO:
        """Classify intent using gRPC"""
        try:
            from voice_assistant.proto import nlu_service_pb2
            from voice_assistant.proto import nlu_service_pb2_grpc
            
            channel = await self.get_nlu_channel()
            stub = nlu_service_pb2_grpc.NLUServiceStub(channel)
            
            request = nlu_service_pb2.IntentRequest(text=text)
            response = await stub.Classify(request)
            
            return IntentDTO(
                name=response.intent,
                confidence=response.confidence,
                entities=dict(response.entities)
            )
        except grpc.aio.AioRpcError as e:
            raise Exception(f"gRPC NLU call failed: {e.details()}")
    
    async def synthesize_speech(self, text: str) -> bytes:
        """Synthesize speech using gRPC"""
        try:
            from voice_assistant.proto import tts_service_pb2
            from voice_assistant.proto import tts_service_pb2_grpc
            
            channel = await self.get_tts_channel()
            stub = tts_service_pb2_grpc.TTSServiceStub(channel)
            
            request = tts_service_pb2.SynthesisRequest(text=text)
            response = await stub.Synthesize(request)
            
            return response.audio_data
        except grpc.aio.AioRpcError as e:
            raise Exception(f"gRPC TTS call failed: {e.details()}")
    
    async def close(self):
        """Close gRPC channels"""
        if self._asr_channel:
            await self._asr_channel.close()
        if self._nlu_channel:
            await self._nlu_channel.close()
        if self._tts_channel:
            await self._tts_channel.close()