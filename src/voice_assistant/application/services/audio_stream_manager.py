"""
Audio Stream Manager for handling RTP audio processing and coordination with downstream services.
"""
import grpc
import asyncio
import logging
from typing import AsyncIterator, Optional, Dict, Any, List
from uuid import UUID
import base64
from datetime import datetime

from voice_assistant.domain.value_objects.audio_chunk import AudioChunk
from voice_assistant.interfaces.container import Config

logger = logging.getLogger(__name__)

class AudioStreamManager:
    """Manages audio chunk processing and streaming coordination"""
    
    def __init__(self, config: Config):
        self.config = config
        self.asr_channels: Dict[str, grpc.Channel] = {}
        self.nlu_channels: Dict[str, grpc.Channel] = {}
        self.tts_channels: Dict[str, grpc.Channel] = {}
        self.active_streams: Dict[UUID, asyncio.Task] = {}
        self._connection_lock = asyncio.Lock()
        
        # Audio processing settings
        self.chunk_duration_ms = config.audio_chunk_duration_ms  # 200ms
        self.sample_rate = config.audio_sample_rate  # 8000 Hz
        self.channels = config.audio_channels  # 1 (mono)
        self.bytes_per_sample = 2  # 16-bit audio
        
        # Calculate chunk size in bytes
        self.chunk_size_bytes = int(
            (self.sample_rate * self.chunk_duration_ms * self.channels * self.bytes_per_sample) / 1000
        )
        
        # gRPC connection settings
        self.grpc_options = [
            ('grpc.max_send_message_length', config.grpc_max_message_length),
            ('grpc.max_receive_message_length', config.grpc_max_message_length),
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000)
        ]
        
        logger.info(f"AudioStreamManager initialized with chunk size: {self.chunk_size_bytes} bytes")
    
    async def initialize_asr_connection(self, asr_service_url: str) -> bool:
        """Initialize gRPC connection to ASR service"""
        async with self._connection_lock:
            if asr_service_url in self.asr_channels:
                # Check if existing connection is healthy
                try:
                    channel = self.asr_channels[asr_service_url]
                    await channel.channel_ready()
                    logger.debug(f"Reusing existing ASR connection to {asr_service_url}")
                    return True
                except grpc.RpcError:
                    # Connection is unhealthy, remove it
                    logger.warning(f"Existing ASR connection to {asr_service_url} is unhealthy, recreating")
                    await self.asr_channels[asr_service_url].close()
                    del self.asr_channels[asr_service_url]
            
            try:
                channel = grpc.aio.insecure_channel(asr_service_url, options=self.grpc_options)
                
                # Test connection with timeout
                await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
                
                # Store channel for reuse
                self.asr_channels[asr_service_url] = channel
                
                logger.info(f"ASR connection established to {asr_service_url}")
                return True
            except asyncio.TimeoutError:
                logger.error(f"Timeout connecting to ASR service at {asr_service_url}")
                return False
            except Exception as e:
                logger.error(f"Failed to connect to ASR service at {asr_service_url}: {e}")
                return False
    
    async def initialize_nlu_connection(self, nlu_service_url: str) -> bool:
        """Initialize gRPC connection to NLU service"""
        async with self._connection_lock:
            if nlu_service_url in self.nlu_channels:
                try:
                    channel = self.nlu_channels[nlu_service_url]
                    await channel.channel_ready()
                    logger.debug(f"Reusing existing NLU connection to {nlu_service_url}")
                    return True
                except grpc.RpcError:
                    logger.warning(f"Existing NLU connection to {nlu_service_url} is unhealthy, recreating")
                    await self.nlu_channels[nlu_service_url].close()
                    del self.nlu_channels[nlu_service_url]
            
            try:
                channel = grpc.aio.insecure_channel(nlu_service_url, options=self.grpc_options)
                await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
                
                self.nlu_channels[nlu_service_url] = channel
                logger.info(f"NLU connection established to {nlu_service_url}")
                return True
            except asyncio.TimeoutError:
                logger.error(f"Timeout connecting to NLU service at {nlu_service_url}")
                return False
            except Exception as e:
                logger.error(f"Failed to connect to NLU service at {nlu_service_url}: {e}")
                return False
    
    async def initialize_tts_connection(self, tts_service_url: str) -> bool:
        """Initialize gRPC connection to TTS service"""
        async with self._connection_lock:
            if tts_service_url in self.tts_channels:
                try:
                    channel = self.tts_channels[tts_service_url]
                    await channel.channel_ready()
                    logger.debug(f"Reusing existing TTS connection to {tts_service_url}")
                    return True
                except grpc.RpcError:
                    logger.warning(f"Existing TTS connection to {tts_service_url} is unhealthy, recreating")
                    await self.tts_channels[tts_service_url].close()
                    del self.tts_channels[tts_service_url]
            
            try:
                channel = grpc.aio.insecure_channel(tts_service_url, options=self.grpc_options)
                await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
                
                self.tts_channels[tts_service_url] = channel
                logger.info(f"TTS connection established to {tts_service_url}")
                return True
            except asyncio.TimeoutError:
                logger.error(f"Timeout connecting to TTS service at {tts_service_url}")
                return False
            except Exception as e:
                logger.error(f"Failed to connect to TTS service at {tts_service_url}: {e}")
                return False
    
    async def close_connections(self):
        """Close all gRPC connections"""
        async with self._connection_lock:
            # Close ASR connections
            for url, channel in self.asr_channels.items():
                try:
                    await channel.close()
                    logger.info(f"Closed ASR connection to {url}")
                except Exception as e:
                    logger.error(f"Error closing ASR connection to {url}: {e}")
            
            # Close NLU connections
            for url, channel in self.nlu_channels.items():
                try:
                    await channel.close()
                    logger.info(f"Closed NLU connection to {url}")
                except Exception as e:
                    logger.error(f"Error closing NLU connection to {url}: {e}")
            
            # Close TTS connections
            for url, channel in self.tts_channels.items():
                try:
                    await channel.close()
                    logger.info(f"Closed TTS connection to {url}")
                except Exception as e:
                    logger.error(f"Error closing TTS connection to {url}: {e}")
            
            self.asr_channels.clear()
            self.nlu_channels.clear()
            self.tts_channels.clear()
    
    def segment_audio_data(self, audio_data: bytes, session_id: UUID) -> List[AudioChunk]:
        """
        Segment raw audio data into 200ms chunks with improved error handling
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            session_id: Session identifier for tracking
            
        Returns:
            List of AudioChunk objects
        """
        if not audio_data:
            logger.warning(f"Empty audio data received for session {session_id}")
            return []
        
        chunks = []
        sequence_number = 0
        
        # Validate audio data length
        if len(audio_data) < self.chunk_size_bytes:
            logger.debug(f"Audio data too small ({len(audio_data)} bytes) for full chunk, padding")
            # Pad with silence if needed
            padded_data = audio_data + b'\x00' * (self.chunk_size_bytes - len(audio_data))
            
            actual_duration = len(audio_data) / (self.sample_rate * self.channels * self.bytes_per_sample)
            
            chunk = AudioChunk.create(
                data=padded_data,
                sample_rate=self.sample_rate,
                channels=self.channels,
                sequence_number=sequence_number,
                duration=actual_duration
            )
            chunks.append(chunk)
            
        else:
            # Process audio in chunk_size_bytes segments
            for i in range(0, len(audio_data), self.chunk_size_bytes):
                chunk_data = audio_data[i:i + self.chunk_size_bytes]
                
                # Handle incomplete chunks at the end
                if len(chunk_data) < self.chunk_size_bytes:
                    if len(chunk_data) >= self.chunk_size_bytes // 2:  # At least 50% of expected size
                        # Pad with silence
                        chunk_data = chunk_data + b'\x00' * (self.chunk_size_bytes - len(chunk_data))
                        logger.debug(f"Padded incomplete chunk {sequence_number} to full size")
                    else:
                        logger.debug(f"Skipping very small incomplete chunk of {len(chunk_data)} bytes")
                        continue
                
                # Calculate actual duration based on original chunk size (before padding)
                original_size = min(len(audio_data) - i, self.chunk_size_bytes)
                actual_duration = original_size / (self.sample_rate * self.channels * self.bytes_per_sample)
                
                chunk = AudioChunk.create(
                    data=chunk_data,
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    sequence_number=sequence_number,
                    duration=actual_duration
                )
                
                chunks.append(chunk)
                sequence_number += 1
        
        logger.debug(f"Segmented {len(audio_data)} bytes into {len(chunks)} chunks for session {session_id}")
        return chunks
    
    def decode_base64_audio(self, base64_audio: str) -> bytes:
        """Decode base64 encoded audio data"""
        try:
            return base64.b64decode(base64_audio)
        except Exception as e:
            logger.error(f"Failed to decode base64 audio: {e}")
            raise ValueError("Invalid base64 audio data")
    
    def audio_chunk_to_protobuf(self, chunk: AudioChunk) -> audio_pb2.AudioChunk:
        """Convert AudioChunk domain object to protobuf message"""
        return audio_pb2.AudioChunk(
            audio_data=chunk.data,
            sample_rate=chunk.sample_rate,
            channels=chunk.channels,
            timestamp_ms=int(chunk.timestamp.timestamp() * 1000),
            sequence_number=chunk.sequence_number,
            duration_ms=int(chunk.duration * 1000),
            is_final=chunk.is_final
        )
    
    def protobuf_to_asr_result(self, pb_result: audio_pb2.ASRResult) -> Dict[str, Any]:
        """Convert protobuf ASRResult to dictionary"""
        return {
            "text": pb_result.text,
            "confidence": pb_result.confidence,
            "is_final": pb_result.is_final,
            "timestamp": datetime.fromtimestamp(pb_result.timestamp_ms / 1000),
            "session_id": pb_result.session_id
        }
    
    async def stream_to_asr(self, session_id: UUID, audio_chunks: List[AudioChunk], 
                           asr_service_url: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream audio chunks to ASR service and yield results
        
        Args:
            session_id: Session identifier
            audio_chunks: List of audio chunks to process
            asr_service_url: ASR service URL (uses default if None)
            
        Yields:
            ASR results as dictionaries
        """
        if not asr_service_url:
            asr_service_url = self.config.asr_service_url
        
        # Ensure connection exists
        if asr_service_url not in self.asr_channels:
            success = await self.initialize_asr_connection(asr_service_url)
            if not success:
                raise RuntimeError(f"Failed to connect to ASR service at {asr_service_url}")
        
        channel = self.asr_channels[asr_service_url]
        stub = audio_pb2_grpc.ASRServiceStub(channel)
        
        try:
            # Create async generator for audio chunks
            async def audio_chunk_generator():
                for chunk in audio_chunks:
                    pb_chunk = self.audio_chunk_to_protobuf(chunk)
                    logger.debug(f"Streaming chunk {chunk.sequence_number} for session {session_id}")
                    yield pb_chunk
                    
                    # Small delay to simulate real-time streaming
                    await asyncio.sleep(0.01)
            
            # Stream to ASR service
            logger.info(f"Starting ASR stream for session {session_id} with {len(audio_chunks)} chunks")
            
            async for asr_result in stub.ProcessAudioStream(audio_chunk_generator()):
                result_dict = self.protobuf_to_asr_result(asr_result)
                logger.debug(f"Received ASR result for session {session_id}: {result_dict['text'][:50]}...")
                yield result_dict
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error during ASR streaming for session {session_id}: {e}")
            raise RuntimeError(f"ASR streaming failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during ASR streaming for session {session_id}: {e}")
            raise
    
    async def stream_to_nlu(self, session_id: UUID, asr_text: str, confidence: float,
                          nlu_service_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send ASR result to NLU service for intent extraction
        
        Args:
            session_id: Session identifier
            asr_text: Transcribed text from ASR
            confidence: ASR confidence score
            nlu_service_url: NLU service URL (uses default if None)
            
        Returns:
            NLU result as dictionary
        """
        if not nlu_service_url:
            nlu_service_url = self.config.nlu_service_url
        
        # Ensure connection exists
        if nlu_service_url not in self.nlu_channels:
            success = await self.initialize_nlu_connection(nlu_service_url)
            if not success:
                raise RuntimeError(f"Failed to connect to NLU service at {nlu_service_url}")
        
        channel = self.nlu_channels[nlu_service_url]
        
        try:
            # Import NLU protobuf (would be implemented when NLU service is ready)
            # For now, return mock response
            logger.info(f"Would send to NLU service: '{asr_text}' with confidence {confidence}")
            
            return {
                "intent": "mock_intent",
                "confidence": 0.8,
                "entities": {},
                "session_id": str(session_id)
            }
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error during NLU processing for session {session_id}: {e}")
            raise RuntimeError(f"NLU processing failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during NLU processing for session {session_id}: {e}")
            raise
    
    async def stream_from_tts(self, session_id: UUID, text: str, voice_config: Optional[Dict[str, str]] = None,
                             tts_service_url: Optional[str] = None) -> AsyncIterator[AudioChunk]:
        """
        Request TTS synthesis and stream audio chunks back
        
        Args:
            session_id: Session identifier
            text: Text to synthesize
            voice_config: Voice configuration parameters
            tts_service_url: TTS service URL (uses default if None)
            
        Yields:
            AudioChunk objects with synthesized speech
        """
        if not tts_service_url:
            tts_service_url = self.config.tts_service_url
        
        # Ensure connection exists
        if tts_service_url not in self.tts_channels:
            success = await self.initialize_tts_connection(tts_service_url)
            if not success:
                raise RuntimeError(f"Failed to connect to TTS service at {tts_service_url}")
        
        channel = self.tts_channels[tts_service_url]
        
        try:
            # Import TTS protobuf (would be implemented when TTS service is ready)
            # For now, yield mock audio chunks
            logger.info(f"Would synthesize TTS for session {session_id}: '{text[:50]}...'")
            
            # Generate mock audio chunks
            mock_audio_data = b'\x00' * self.chunk_size_bytes
            for i in range(3):  # Mock 3 chunks of audio
                chunk = AudioChunk.create(
                    data=mock_audio_data,
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    sequence_number=i,
                    duration=self.chunk_duration_ms / 1000.0
                )
                yield chunk
                await asyncio.sleep(0.01)  # Small delay to simulate streaming
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error during TTS synthesis for session {session_id}: {e}")
            raise RuntimeError(f"TTS synthesis failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during TTS synthesis for session {session_id}: {e}")
            raise
        """
        Stream audio chunks to ASR service and yield results
        
        Args:
            session_id: Session identifier
            audio_chunks: List of audio chunks to process
            asr_service_url: ASR service URL (uses default if None)
            
        Yields:
            ASR results as dictionaries
        """
        if not asr_service_url:
            asr_service_url = self.config.asr_service_url
        
        # Ensure connection exists
        if asr_service_url not in self.asr_channels:
            success = await self.initialize_asr_connection(asr_service_url)
            if not success:
                raise RuntimeError(f"Failed to connect to ASR service at {asr_service_url}")
        
        channel = self.asr_channels[asr_service_url]
        stub = audio_pb2_grpc.ASRServiceStub(channel)
        
        try:
            # Create async generator for audio chunks
            async def audio_chunk_generator():
                for chunk in audio_chunks:
                    pb_chunk = self.audio_chunk_to_protobuf(chunk)
                    logger.debug(f"Streaming chunk {chunk.sequence_number} for session {session_id}")
                    yield pb_chunk
                    
                    # Small delay to simulate real-time streaming
                    await asyncio.sleep(0.01)
            
            # Stream to ASR service
            logger.info(f"Starting ASR stream for session {session_id} with {len(audio_chunks)} chunks")
            
            async for asr_result in stub.ProcessAudioStream(audio_chunk_generator()):
                result_dict = self.protobuf_to_asr_result(asr_result)
                logger.debug(f"Received ASR result for session {session_id}: {result_dict['text'][:50]}...")
                yield result_dict
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error during ASR streaming for session {session_id}: {e}")
            raise RuntimeError(f"ASR streaming failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during ASR streaming for session {session_id}: {e}")
            raise
    
    async def process_rtp_audio(self, session_id: UUID, base64_audio: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Process RTP audio data through the complete pipeline
        
        Args:
            session_id: Session identifier
            base64_audio: Base64 encoded audio data
            
        Yields:
            ASR results from processing
        """
        try:
            # Decode audio data
            audio_data = self.decode_base64_audio(base64_audio)
            logger.info(f"Processing {len(audio_data)} bytes of audio for session {session_id}")
            
            # Segment into chunks
            chunks = self.segment_audio_data(audio_data, session_id)
            
            if not chunks:
                logger.warning(f"No valid audio chunks generated for session {session_id}")
                return
            
            # Stream to ASR and yield results
            async for result in self.stream_to_asr(session_id, chunks):
                yield result
                
        except Exception as e:
            logger.error(f"Error processing RTP audio for session {session_id}: {e}")
            raise
    
    async def start_session_with_asr(self, session_id: UUID, language: str = "ru", 
                                   config_params: Optional[Dict[str, str]] = None) -> bool:
        """Start a session with ASR service"""
        asr_service_url = self.config.asr_service_url
        
        if asr_service_url not in self.asr_channels:
            success = await self.initialize_asr_connection(asr_service_url)
            if not success:
                return False
        
        channel = self.asr_channels[asr_service_url]
        stub = audio_pb2_grpc.ASRServiceStub(channel)
        
        try:
            request = audio_pb2.ASRRequest(
                session_id=str(session_id),
                language=language,
                config=config_params or {}
            )
            
            response = await stub.StartSession(request)
            
            if response.success:
                logger.info(f"Started ASR session {session_id}: {response.message}")
                return True
            else:
                logger.error(f"Failed to start ASR session {session_id}: {response.message}")
                return False
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error starting ASR session {session_id}: {e}")
            return False
    
    async def end_session_with_asr(self, session_id: UUID) -> bool:
        """End a session with ASR service"""
        asr_service_url = self.config.asr_service_url
        
        if asr_service_url not in self.asr_channels:
            logger.warning(f"No ASR connection found for ending session {session_id}")
            return True  # Consider it successful if no connection exists
        
        channel = self.asr_channels[asr_service_url]
        stub = audio_pb2_grpc.ASRServiceStub(channel)
        
        try:
            request = audio_pb2.SessionRequest(session_id=str(session_id))
            response = await stub.EndSession(request)
            
            if response.success:
                logger.info(f"Ended ASR session {session_id}: {response.message}")
                return True
            else:
                logger.error(f"Failed to end ASR session {session_id}: {response.message}")
                return False
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error ending ASR session {session_id}: {e}")
            return False
    
    async def process_complete_pipeline(self, session_id: UUID, base64_audio: str,
                                      language: str = "ru") -> Dict[str, Any]:
        """
        Process audio through the complete pipeline: ASR -> NLU -> Dialog
        
        Args:
            session_id: Session identifier
            base64_audio: Base64 encoded audio data
            language: Language code for processing
            
        Returns:
            Complete processing result with ASR, NLU, and Dialog outputs
        """
        try:
            # Step 1: Process audio through ASR
            asr_results = []
            async for result in self.process_rtp_audio(session_id, base64_audio):
                asr_results.append(result)
                
                # Process final results through NLU
                if result.get('is_final', False):
                    text = result.get('text', '')
                    confidence = result.get('confidence', 0.0)
                    
                    if text and confidence > 0.3:  # Minimum confidence threshold
                        # Step 2: Send to NLU for intent extraction
                        nlu_result = await self.stream_to_nlu(session_id, text, confidence)
                        
                        # Step 3: Generate response text (would integrate with Dialog service)
                        response_text = f"Понял: {text}"  # Mock response in Russian
                        
                        # Step 4: Synthesize response through TTS
                        tts_chunks = []
                        async for chunk in self.stream_from_tts(session_id, response_text):
                            tts_chunks.append(chunk)
                        
                        return {
                            "session_id": str(session_id),
                            "asr_results": asr_results,
                            "nlu_result": nlu_result,
                            "response_text": response_text,
                            "tts_chunks": len(tts_chunks),
                            "processing_complete": True
                        }
            
            # If no final results with sufficient confidence
            return {
                "session_id": str(session_id),
                "asr_results": asr_results,
                "error": "No final ASR results with sufficient confidence",
                "processing_complete": False
            }
            
        except Exception as e:
            logger.error(f"Error in complete pipeline processing for session {session_id}: {e}")
            return {
                "session_id": str(session_id),
                "error": str(e),
                "processing_complete": False
            }
    
    def get_stream_stats(self) -> Dict[str, Any]:
        """Get statistics about active streams and connections"""
        return {
            "active_streams": len(self.active_streams),
            "asr_connections": len(self.asr_channels),
            "nlu_connections": len(self.nlu_channels),
            "tts_connections": len(self.tts_channels),
            "total_connections": len(self.asr_channels) + len(self.nlu_channels) + len(self.tts_channels),
            "chunk_size_bytes": self.chunk_size_bytes,
            "chunk_duration_ms": self.chunk_duration_ms,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bytes_per_sample": self.bytes_per_sample
        }