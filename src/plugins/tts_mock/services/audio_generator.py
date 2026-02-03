"""
Audio generator for Mock TTS.
"""

import struct
from typing import Optional

from ..interfaces import IAudioGenerator, IDelaySimulator


class WavAudioGenerator(IAudioGenerator):
    """
    Generates simple WAV audio data.
    
    Creates a valid WAV file header with dummy audio data.
    """
    
    def __init__(self, sample_rate: int = 16000, duration_ms: int = 500):
        """
        Initialize generator.
        
        Args:
            sample_rate: Audio sample rate
            duration_ms: Duration of generated audio in milliseconds
        """
        self.sample_rate = sample_rate
        self.duration_ms = duration_ms
    
    def generate(self, text: str) -> bytes:
        """
        Generate WAV audio data.
        
        Args:
            text: Text to synthesize (used to determine duration)
            
        Returns:
            WAV audio data as bytes
        """
        # Calculate duration based on text length (approximate)
        # ~100ms per character
        duration_ms = max(self.duration_ms, len(text) * 100)
        num_samples = int(self.sample_rate * (duration_ms / 1000.0))
        
        # Generate simple sine wave
        import math
        frequency = 440  # A4 note
        samples = []
        
        for i in range(num_samples):
            # Simple sine wave
            value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / self.sample_rate))
            samples.append(value)
        
        # Create WAV data
        audio_data = struct.pack('<' + 'h' * len(samples), *samples)
        
        # Create WAV header
        wav_header = self._create_wav_header(len(audio_data))
        
        return wav_header + audio_data
    
    def _create_wav_header(self, data_size: int) -> bytes:
        """
        Create WAV file header.
        
        Args:
            data_size: Size of audio data in bytes
            
        Returns:
            WAV header bytes
        """
        num_channels = 1
        bits_per_sample = 16
        byte_rate = self.sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        
        header = b'RIFF'
        header += struct.pack('<I', 36 + data_size)  # File size
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 16)  # Subchunk size
        header += struct.pack('<H', 1)  # Audio format (PCM)
        header += struct.pack('<H', num_channels)
        header += struct.pack('<I', self.sample_rate)
        header += struct.pack('<I', byte_rate)
        header += struct.pack('<H', block_align)
        header += struct.pack('<H', bits_per_sample)
        header += b'data'
        header += struct.pack('<I', data_size)
        
        return header


class DelaySimulator(IDelaySimulator):
    """
    Simulates processing delay.
    
    Useful for testing timeout handling and async behavior.
    """
    
    def __init__(self, delay_ms: int = 0):
        """
        Initialize simulator.
        
        Args:
            delay_ms: Delay in milliseconds
        """
        self.delay_ms = delay_ms
    
    async def simulate_delay(self) -> None:
        """Simulate processing delay."""
        if self.delay_ms > 0:
            import asyncio
            await asyncio.sleep(self.delay_ms / 1000.0)
