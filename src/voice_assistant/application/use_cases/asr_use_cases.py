"""
ASR Use Cases for ASR Service.

User goal: Transcribe audio to text with fallback support.
Success guarantee: Returns transcription or error indication.
Side effects: Updates session statistics.
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from ...domain.value_objects.audio_chunk import AudioChunk
from ...application.dto.transcription_dto import TranscriptionDTO
from ...infrastructure.plugins.plugin_interface import ASRPlugin
from ...infrastructure.resilience.circuit_breaker import CircuitBreaker


class TranscribeAudioUseCase:
    """
    Use case for transcribing audio with fallback support.
    
    Uses primary ASR engine with fallback to secondary engine.
    Implements circuit breaker pattern for resilience.
    """
    
    def __init__(
        self,
        primary_asr: ASRPlugin,
        fallback_asr: Optional[ASRPlugin],
        primary_circuit_breaker: CircuitBreaker,
        fallback_circuit_breaker: Optional[CircuitBreaker],
        confidence_threshold: float = 0.7
    ):
        self.primary_asr = primary_asr
        self.fallback_asr = fallback_asr
        self.primary_circuit_breaker = primary_circuit_breaker
        self.fallback_circuit_breaker = fallback_circuit_breaker
        self.confidence_threshold = confidence_threshold
    
    async def execute(
        self,
        audio_chunk: AudioChunk,
        session_id: str,
        session_stats: Dict[str, Any]
    ) -> TranscriptionDTO:
        """
        Transcribe audio with fallback logic.
        
        Args:
            audio_chunk: Audio data to transcribe
            session_id: Session identifier
            session_stats: Session statistics dictionary
            
        Returns:
            Transcription result
        """
        primary_result = None
        primary_error = None
        fallback_result = None
        fallback_error = None
        
        # Try primary ASR
        if (self.primary_asr and 
            self.primary_circuit_breaker and 
            self.primary_circuit_breaker.can_execute()):
            
            try:
                primary_result = await self.primary_asr.transcribe(audio_chunk)
                self.primary_circuit_breaker.record_success()
                
                if primary_result.is_final:
                    if primary_result.confidence >= self.confidence_threshold:
                        session_stats['primary_successes'] = session_stats.get('primary_successes', 0) + 1
                        return primary_result
                    else:
                        session_stats['low_confidence_results'] = session_stats.get('low_confidence_results', 0) + 1
                else:
                    return primary_result
                    
            except Exception as e:
                primary_error = e
                self.primary_circuit_breaker.record_failure()
                session_stats['primary_failures'] = session_stats.get('primary_failures', 0) + 1
        
        # Try fallback for final results
        should_try_fallback = (
            self.fallback_asr and 
            self.fallback_circuit_breaker and
            self.fallback_circuit_breaker.can_execute() and
            audio_chunk.is_final and
            (primary_result is None or 
             (primary_result.is_final and primary_result.confidence < self.confidence_threshold))
        )
        
        if should_try_fallback:
            try:
                fallback_result = await self.fallback_asr.transcribe(audio_chunk)
                self.fallback_circuit_breaker.record_success()
                
                if primary_result and fallback_result:
                    if fallback_result.confidence > primary_result.confidence:
                        session_stats['fallback_used'] = session_stats.get('fallback_used', 0) + 1
                        return fallback_result
                    else:
                        return primary_result
                elif fallback_result:
                    session_stats['fallback_used'] = session_stats.get('fallback_used', 0) + 1
                    return fallback_result
                    
            except Exception as e:
                fallback_error = e
                self.fallback_circuit_breaker.record_failure()
                session_stats['fallback_failures'] = session_stats.get('fallback_failures', 0) + 1
        
        # Return primary result if available
        if primary_result:
            if primary_result.is_final and primary_result.confidence < self.confidence_threshold:
                primary_result.text = f"[LOW_CONFIDENCE] {primary_result.text}"
            return primary_result
        
        # Create error result
        error_text = "[ASR_ERROR]"
        if primary_error and fallback_error:
            error_text = f"[ASR_ERROR] Primary: {str(primary_error)[:50]}, Fallback: {str(fallback_error)[:50]}"
        elif primary_error:
            error_text = f"[ASR_ERROR] Primary: {str(primary_error)[:100]}"
        elif fallback_error:
            error_text = f"[ASR_ERROR] Fallback: {str(fallback_error)[:100]}"
        
        session_stats['total_failures'] = session_stats.get('total_failures', 0) + 1
        
        return TranscriptionDTO(
            text=error_text,
            is_final=True,
            confidence=0.0,
            timestamp=datetime.utcnow(),
            audio_duration=audio_chunk.duration
        )


class ManageASRSessionUseCase:
    """Use case for managing ASR sessions."""
    
    def __init__(
        self,
        primary_asr: ASRPlugin,
        fallback_asr: Optional[ASRPlugin]
    ):
        self.primary_asr = primary_asr
        self.fallback_asr = fallback_asr
    
    async def start_session(self, session_id: str) -> Tuple[bool, str]:
        """
        Start ASR session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (success, message)
        """
        success_count = 0
        errors = []
        
        if self.primary_asr:
            try:
                await self.primary_asr.start_recognition_session(session_id)
                success_count += 1
            except Exception as e:
                errors.append(f"Primary: {e}")
        
        if self.fallback_asr and self.fallback_asr.is_available():
            try:
                await self.fallback_asr.start_recognition_session(session_id)
                success_count += 1
            except Exception as e:
                errors.append(f"Fallback: {e}")
        
        if success_count == 0:
            return False, f"No ASR plugins available. Errors: {', '.join(errors)}"
        
        return True, f"Session started with {success_count} ASR engine(s)"
    
    async def end_session(self, session_id: str) -> Tuple[bool, str]:
        """
        End ASR session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (success, message)
        """
        if self.primary_asr:
            try:
                await self.primary_asr.end_recognition_session(session_id)
            except Exception as e:
                pass  # Log but don't fail
        
        if self.fallback_asr:
            try:
                await self.fallback_asr.end_recognition_session(session_id)
            except Exception as e:
                pass  # Log but don't fail
        
        return True, "Session ended"
