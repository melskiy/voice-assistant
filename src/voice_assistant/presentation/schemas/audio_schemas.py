"""
Pydantic schemas for audio processing endpoints.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class AudioChunkRequest(BaseModel):
    """Audio chunk request from client"""
    session_id: str = Field(..., description="Session ID for the audio stream")
    audio_data: str = Field(..., description="Base64 encoded audio data")
    sample_rate: int = Field(8000, ge=8000, le=48000, description="Audio sample rate in Hz")
    channels: int = Field(1, ge=1, le=2, description="Number of audio channels")
    encoding: str = Field("pcm", description="Audio encoding format (pcm, wav, etc.)")

    @field_validator('audio_data')
    @classmethod
    def validate_audio_data(cls, v: str) -> str:
        """Validate that audio data is not empty"""
        if not v or len(v) < 10:
            raise ValueError("Audio data must be a valid base64 string")
        return v


class ProcessAudioRequest(BaseModel):
    """Request to process audio chunk"""
    session_id: str = Field(..., description="Session ID")
    audio_chunk: AudioChunkRequest = Field(..., description="Audio chunk data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional processing metadata")


class ASRResult(BaseModel):
    """ASR (Automatic Speech Recognition) result"""
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence")
    is_final: bool = Field(True, description="Whether this is a final result")
    timestamp: Optional[datetime] = Field(None, description="Result timestamp")
    session_id: Optional[str] = Field(None, description="Session ID")


class AudioProcessingResponse(BaseModel):
    """Response from audio processing"""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Processing status")
    response_text: str = Field(..., description="Response text to play back")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    is_final: bool = Field(True, description="Whether processing is complete")
    timestamp: float = Field(..., description="Response timestamp")
    asr_results_count: int = Field(0, ge=0, description="Number of ASR results")
    asr_results: Optional[List[ASRResult]] = Field(None, description="Detailed ASR results")


class AudioStreamStats(BaseModel):
    """Statistics for a single audio stream"""
    session_id: str = Field(..., description="Session ID")
    bytes_received: int = Field(0, ge=0, description="Total bytes received")
    chunks_processed: int = Field(0, ge=0, description="Number of chunks processed")
    duration_seconds: float = Field(0.0, ge=0.0, description="Total audio duration")
    average_chunk_size: float = Field(0.0, ge=0.0, description="Average chunk size in bytes")


class AudioStatsResponse(BaseModel):
    """Audio stream statistics response"""
    status: str = Field(..., description="Response status")
    stats: Dict[str, Any] = Field(..., description="Audio statistics")
    timestamp: float = Field(..., description="Response timestamp")
    active_streams: int = Field(0, ge=0, description="Number of active streams")
    total_streams_processed: int = Field(0, ge=0, description="Total streams processed")