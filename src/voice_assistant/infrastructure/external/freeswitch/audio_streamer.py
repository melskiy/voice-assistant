import asyncio
import json
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import aio_pika
from voice_assistant.domain.value_objects.audio_chunk import AudioChunk


class AudioStreamer:
    """Handles audio streaming between FreeSWITCH and voice assistant core"""
    
    def __init__(self, session_id: str, call_uuid: str, rabbitmq_url: str = "amqp://guest:guest@localhost/"):
        self.session_id = session_id
        self.call_uuid = call_uuid
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.response_queue: Optional[aio_pika.Queue] = None
        self.audio_response_buffer = []
    
    async def connect(self):
        """Establish connection to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        
        # Declare exchanges and queues
        exchange = await self.channel.declare_exchange(
            "voice_assistant_exchange",
            aio_pika.ExchangeType.TOPIC
        )
        
        # Queue for sending audio chunks to ASR service
        audio_input_queue = await self.channel.declare_queue(
            f"asr.input.{self.session_id}",
            durable=True
        )
        await audio_input_queue.bind(exchange, routing_key="asr.input")
        
        # Queue for receiving TTS responses
        self.response_queue = await self.channel.declare_queue(
            f"tts.output.{self.session_id}",
            durable=True
        )
        await self.response_queue.bind(exchange, routing_key=f"tts.output.{self.session_id}")
        
        # Start consuming responses
        await self.response_queue.consume(self._on_tts_response)
    
    async def send_audio_chunk(self, audio_chunk: AudioChunk):
        """Send audio chunk to ASR service via RabbitMQ"""
        if not self.channel:
            await self.connect()
        
        message_body = {
            "message_type": "audio_chunk",
            "session_id": self.session_id,
            "call_uuid": self.call_uuid,
            "chunk_id": str(audio_chunk.id),
            "audio_data": audio_chunk.data.hex(),  # Convert bytes to hex for JSON
            "sample_rate": audio_chunk.sample_rate,
            "channels": audio_chunk.channels,
            "timestamp": audio_chunk.timestamp.isoformat(),
            "sequence_number": audio_chunk.sequence_number,
            "is_final": audio_chunk.is_final
        }
        
        message = aio_pika.Message(
            json.dumps(message_body).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        exchange = await self.channel.declare_exchange(
            "voice_assistant_exchange",
            aio_pika.ExchangeType.TOPIC
        )
        
        await exchange.publish(
            message,
            routing_key="asr.input"
        )
    
    async def _on_tts_response(self, message: aio_pika.IncomingMessage):
        """Handle incoming TTS response from the system"""
        async with message.process():
            try:
                response_data = json.loads(message.body.decode())
                
                if response_data.get("session_id") == self.session_id:
                    audio_hex = response_data.get("audio_data")
                    if audio_hex:
                        audio_bytes = bytes.fromhex(audio_hex)
                        self.audio_response_buffer.append(audio_bytes)
                        
            except Exception as e:
                print(f"Error processing TTS response: {e}")
    
    def check_for_responses(self) -> Optional[bytes]:
        """Check for any buffered TTS responses"""
        if self.audio_response_buffer:
            return self.audio_response_buffer.pop(0)
        return None
    
    async def cleanup(self):
        """Clean up connections"""
        if self.connection:
            await self.connection.close()


class FreeSWITCHAudioCapture:
    """Wrapper for FreeSWITCH audio capture functionality"""
    
    def __init__(self, session):
        self.session = session
        self.sample_rate = 8000  # Standard telephony rate
        self.channels = 1  # Mono
        self.chunk_size = 320  # 20ms at 8kHz mono 16-bit
    
    def read_audio_chunk(self) -> Optional[AudioChunk]:
        """Read an audio chunk from FreeSWITCH session"""
        try:
            # This would use FreeSWITCH's audio APIs
            # The exact implementation depends on the FreeSWITCH version
            # and available Python bindings
            
            # Placeholder implementation
            # In practice, this would interface with FreeSWITCH's audio system
            # to capture raw PCM data
            
            # Simulate reading audio data
            audio_data = self._read_raw_audio()
            if audio_data:
                return AudioChunk(
                    id=uuid.uuid4(),
                    data=audio_data,
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    timestamp=datetime.utcnow(),
                    sequence_number=0,  # Would increment
                    duration=len(audio_data) / (self.sample_rate * self.channels * 2),  # Assuming 16-bit
                    is_final=False
                )
            return None
        except Exception as e:
            print(f"Error reading audio chunk: {e}")
            return None
    
    def _read_raw_audio(self) -> Optional[bytes]:
        """Read raw audio bytes from FreeSWITCH (implementation-specific)"""
        # This is a placeholder - the actual implementation would depend
        # on the specific FreeSWITCH Python API being used
        pass