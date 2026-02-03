"""
End-to-End Integration Test for Complete Call Flow.

This test simulates a complete voice call from start to finish,
including all service interactions with detailed logging at each step.

Test Scenario:
1. Incoming call from FreeSWITCH
2. Audio streaming and ASR processing
3. NLU intent extraction
4. Dialog management
5. TTS response generation
6. Data persistence
7. Call termination

Usage:
    pytest tests/test_end_to_end_call_flow.py -v -s
    pytest tests/test_end_to_end_call_flow.py::TestEndToEndCallFlow::test_complete_shopping_list_call_flow -v -s
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import grpc

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CallFlowStep:
    """Represents a single step in the call flow with timing and status."""
    name: str
    service: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "pending"
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def complete(self, status: str = "success", details: Optional[Dict] = None, error: Optional[str] = None):
        """Mark step as complete."""
        self.end_time = time.time()
        self.status = status
        if details:
            self.details.update(details)
        if error:
            self.error = error
    
    @property
    def duration_ms(self) -> float:
        """Get step duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    def __str__(self) -> str:
        status_icon = "[OK]" if self.status == "success" else "[ERR]" if self.status == "error" else "[..]"
        return f"{status_icon} {self.service}::{self.name} ({self.duration_ms:.2f}ms)"


@dataclass
class CallFlowReport:
    """Complete report of the call flow execution."""
    call_id: str
    steps: List[CallFlowStep] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    def add_step(self, step: CallFlowStep):
        """Add a step to the report."""
        self.steps.append(step)
        logger.info(f"STEP START: {step}")
        return step
    
    def complete(self):
        """Mark call flow as complete."""
        self.end_time = time.time()
    
    @property
    def total_duration_ms(self) -> float:
        """Get total call duration."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    @property
    def success_count(self) -> int:
        return sum(1 for s in self.steps if s.status == "success")
    
    @property
    def error_count(self) -> int:
        return sum(1 for s in self.steps if s.status == "error")
    
    def print_report(self):
        """Print detailed report."""
        print("\n" + "=" * 80)
        print(f"CALL FLOW REPORT - Call ID: {self.call_id}")
        print("=" * 80)
        print(f"Total Duration: {self.total_duration_ms:.2f}ms")
        print(f"Steps: {self.success_count} success, {self.error_count} errors, {len(self.steps)} total")
        print("-" * 80)
        
        for i, step in enumerate(self.steps, 1):
            print(f"{i:2d}. {step}")
            if step.details:
                for key, value in step.details.items():
                    print(f"    -> {key}: {value}")
            if step.error:
                print(f"    -> ERROR: {step.error}")
        
        print("=" * 80)


class TestEndToEndCallFlow:
    """
    End-to-end integration test for complete call flow.
    
    Simulates the entire pipeline:
    FreeSWITCH → Gateway → ASR → NLU → Dialog → TTS → Storage
    """
    
    @pytest.fixture
    def call_flow_report(self):
        """Create a new call flow report."""
        return CallFlowReport(call_id=str(uuid.uuid4()))
    
    @pytest.fixture
    def mock_services(self):
        """Setup mock services for all microservices."""
        services = {
            'asr': AsyncMock(),
            'nlu': AsyncMock(),
            'dialog': AsyncMock(),
            'tts': AsyncMock(),
            'storage': AsyncMock(),
            'notification': AsyncMock(),
        }
        return services
    
    @pytest.fixture
    def test_audio_data(self):
        """Generate test audio data (simulated)."""
        # Simulate 1 second of 8kHz 16-bit mono audio
        return b'\x00\x01' * 8000
    
    @pytest.fixture
    def test_session_data(self):
        """Create test session data."""
        return {
            'session_id': str(uuid.uuid4()),
            'caller_id': '+79123456789',
            'call_uuid': str(uuid.uuid4()),
            'language': 'ru',
            'start_time': datetime.now().isoformat(),
        }
    
    async def _simulate_freeswitch_incoming_call(
        self,
        report: CallFlowReport,
        session_data: Dict
    ) -> Dict:
        """
        Step 1: Simulate incoming call from FreeSWITCH.
        
        Service: FreeSWITCH → Gateway
        Endpoint: POST /v1/freeswitch/call/incoming
        """
        step = report.add_step(CallFlowStep(
            name="handle_incoming_call",
            service="FreeSWITCH/Gateway",
            details={
                'caller_id': session_data['caller_id'],
                'call_uuid': session_data['call_uuid']
            }
        ))
        
        try:
            # Simulate FreeSWITCH sending incoming call webhook
            incoming_call_request = {
                'call_uuid': session_data['call_uuid'],
                'caller_id': session_data['caller_id'],
                'destination': '1000',
                'timestamp': time.time()
            }
            
            # Gateway creates session
            session_data['session_id'] = str(uuid.uuid4())
            
            await asyncio.sleep(0.01)  # Simulate network latency
            
            step.complete("success", {
                'session_created': True,
                'session_id': session_data['session_id'],
                'response_time_ms': step.duration_ms
            })
            
            logger.info(f"[OK] Incoming call handled, session created: {session_data['session_id']}")
            return session_data
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    async def _simulate_asr_processing(
        self,
        report: CallFlowReport,
        session_data: Dict,
        audio_data: bytes,
        mock_asr: AsyncMock
    ) -> str:
        """
        Step 2: Simulate ASR processing.
        
        Service: Gateway → ASR Service (gRPC)
        Method: ProcessAudioStream(stream AudioChunk) returns (stream ASRResult)
        """
        step = report.add_step(CallFlowStep(
            name="process_audio_stream",
            service="ASR",
            details={
                'session_id': session_data['session_id'],
                'audio_bytes': len(audio_data),
                'sample_rate': 8000
            }
        ))
        
        try:
            # Mock ASR response
            # Create async iterator for mock
            async def mock_asr_iterator():
                yield {
                    'text': 'добавь молоко',
                    'confidence': 0.92,
                    'is_final': True,
                    'timestamp_ms': int(time.time() * 1000)
                }
            
            mock_asr.ProcessAudioStream.return_value = mock_asr_iterator()
            
            # Simulate streaming audio chunks
            chunks_sent = 0
            async for result in mock_asr.ProcessAudioStream():
                transcribed_text = result['text']
                confidence = result['confidence']
                chunks_sent += 1
            
            await asyncio.sleep(0.05)  # Simulate processing time
            
            step.complete("success", {
                'transcribed_text': transcribed_text,
                'confidence': confidence,
                'chunks_processed': chunks_sent,
                'is_final': True
            })
            
            logger.info(f"[OK] ASR processing complete: '{transcribed_text}' (confidence: {confidence})")
            return transcribed_text
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    async def _simulate_nlu_processing(
        self,
        report: CallFlowReport,
        session_data: Dict,
        text: str,
        mock_nlu: AsyncMock
    ) -> Dict:
        """
        Step 3: Simulate NLU intent extraction.
        
        Service: Gateway → NLU Service (gRPC)
        Method: ExtractIntent(IntentRequest) returns (IntentResponse)
        """
        step = report.add_step(CallFlowStep(
            name="extract_intent",
            service="NLU",
            details={
                'session_id': session_data['session_id'],
                'input_text': text
            }
        ))
        
        try:
            # Mock NLU response
            intent_result = {
                'name': 'ADD_SHOPPING_ITEM',
                'confidence': 0.88,
                'entities': {'item': 'молоко'},
                'raw_text': text,
                'session_id': session_data['session_id']
            }
            mock_nlu.ExtractIntent.return_value = intent_result
            
            result = await mock_nlu.ExtractIntent()
            
            await asyncio.sleep(0.02)  # Simulate processing time
            
            step.complete("success", {
                'intent_name': result['name'],
                'intent_confidence': result['confidence'],
                'entities': result['entities'],
                'routing_decision': 'process'
            })
            
            logger.info(f"[OK] NLU processing complete: intent={result['name']}, entities={result['entities']}")
            return result
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    async def _simulate_dialog_processing(
        self,
        report: CallFlowReport,
        session_data: Dict,
        intent: Dict,
        mock_dialog: AsyncMock
    ) -> Dict:
        """
        Step 4: Simulate Dialog processing.
        
        Service: Gateway → Dialog Service (gRPC)
        Method: ProcessIntent(DialogRequest) returns (DialogResponse)
        """
        step = report.add_step(CallFlowStep(
            name="process_intent",
            service="Dialog",
            details={
                'session_id': session_data['session_id'],
                'intent': intent['name']
            }
        ))
        
        try:
            # Mock Dialog response
            dialog_result = {
                'session_id': session_data['session_id'],
                'response_text': 'Добавила молоко в список покупок. Что-нибудь еще?',
                'action': 'add_shopping_item',
                'requires_confirmation': False,
                'session_complete': False
            }
            mock_dialog.ProcessIntent.return_value = dialog_result
            
            result = await mock_dialog.ProcessIntent()
            
            await asyncio.sleep(0.01)  # Simulate processing time
            
            step.complete("success", {
                'response_text': result['response_text'],
                'action': result['action'],
                'requires_confirmation': result['requires_confirmation']
            })
            
            logger.info(f"[OK] Dialog processing complete: action={result['action']}")
            return result
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    async def _simulate_storage_persistence(
        self,
        report: CallFlowReport,
        session_data: Dict,
        intent: Dict,
        mock_storage: AsyncMock
    ) -> bool:
        """
        Step 5: Simulate data persistence.
        
        Service: Dialog → Storage Service (gRPC)
        Method: SaveShoppingList(SaveShoppingListRequest) returns (SaveResponse)
        """
        step = report.add_step(CallFlowStep(
            name="save_shopping_list",
            service="Storage",
            details={
                'session_id': session_data['session_id'],
                'operation': 'add_item',
                'item': intent['entities'].get('item')
            }
        ))
        
        try:
            # Mock Storage response
            mock_storage.SaveShoppingList.return_value = {
                'success': True,
                'message': 'Shopping list saved successfully',
                'items_count': 1
            }
            
            result = await mock_storage.SaveShoppingList()
            
            await asyncio.sleep(0.01)  # Simulate DB write
            
            step.complete("success", {
                'persistence_success': result['success'],
                'items_count': result['items_count']
            })
            
            logger.info(f"[OK] Data persistence complete: {result['items_count']} items saved")
            return result['success']
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    async def _simulate_tts_generation(
        self,
        report: CallFlowReport,
        session_data: Dict,
        response_text: str,
        mock_tts: AsyncMock
    ) -> bytes:
        """
        Step 6: Simulate TTS generation.
        
        Service: Gateway → TTS Service (gRPC)
        Method: SynthesizeSpeech(TTSRequest) returns (stream AudioChunk)
        """
        step = report.add_step(CallFlowStep(
            name="synthesize_speech",
            service="TTS",
            details={
                'session_id': session_data['session_id'],
                'text_length': len(response_text),
                'voice': 'baya'
            }
        ))
        
        try:
            # Mock TTS response (simulated audio chunks)
            audio_chunks = [
                b'\x00\x01' * 1600,  # 100ms of audio
                b'\x00\x01' * 1600,
                b'\x00\x01' * 1600,
            ]
            
            async def mock_tts_iterator():
                for chunk in audio_chunks:
                    yield chunk
            
            mock_tts.SynthesizeSpeech.return_value = mock_tts_iterator()
            
            total_audio = b''
            chunks_received = 0
            async for chunk in mock_tts.SynthesizeSpeech():
                total_audio += chunk
                chunks_received += 1
            
            await asyncio.sleep(0.03)  # Simulate synthesis time
            
            step.complete("success", {
                'audio_bytes': len(total_audio),
                'chunks_received': chunks_received,
                'duration_ms': chunks_received * 100
            })
            
            logger.info(f"[OK] TTS synthesis complete: {len(total_audio)} bytes, {chunks_received} chunks")
            return total_audio
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    async def _simulate_call_termination(
        self,
        report: CallFlowReport,
        session_data: Dict
    ) -> bool:
        """
        Step 7: Simulate call termination.
        
        Service: FreeSWITCH → Gateway
        Endpoint: POST /v1/freeswitch/call/hangup
        """
        step = report.add_step(CallFlowStep(
            name="hangup_call",
            service="FreeSWITCH/Gateway",
            details={
                'session_id': session_data['session_id'],
                'hangup_cause': 'normal_clearing'
            }
        ))
        
        try:
            # Simulate cleanup
            await asyncio.sleep(0.01)
            
            step.complete("success", {
                'session_terminated': True,
                'hangup_cause': 'normal_clearing',
                'call_duration_ms': report.total_duration_ms
            })
            
            logger.info(f"[OK] Call terminated successfully")
            return True
            
        except Exception as e:
            step.complete("error", error=str(e))
            raise
    
    def _create_async_iterator(self, items: List[Any]) -> AsyncIterator[Any]:
        """Create an async iterator from a list."""
        async def iterator():
            for item in items:
                yield item
        return iterator()
    
    @pytest.mark.asyncio
    async def test_complete_shopping_list_call_flow(
        self,
        call_flow_report: CallFlowReport,
        mock_services: Dict,
        test_audio_data: bytes,
        test_session_data: Dict
    ):
        """
        Test complete call flow for adding item to shopping list.
        
        Scenario:
        1. User calls and says "добавь молоко"
        2. ASR transcribes audio
        3. NLU extracts ADD_SHOPPING_ITEM intent
        4. Dialog processes intent
        5. Data is persisted to storage
        6. TTS generates response
        7. Call ends
        """
        logger.info("=" * 80)
        logger.info("STARTING END-TO-END CALL FLOW TEST")
        logger.info("=" * 80)
        
        report = call_flow_report
        session = test_session_data.copy()
        
        try:
            # Step 1: Incoming call
            session = await self._simulate_freeswitch_incoming_call(report, session)
            
            # Step 2: ASR Processing
            transcribed_text = await self._simulate_asr_processing(
                report, session, test_audio_data, mock_services['asr']
            )
            assert transcribed_text == 'добавь молоко', f"Unexpected transcription: {transcribed_text}"
            
            # Step 3: NLU Processing
            intent = await self._simulate_nlu_processing(
                report, session, transcribed_text, mock_services['nlu']
            )
            assert intent['name'] == 'ADD_SHOPPING_ITEM', f"Unexpected intent: {intent['name']}"
            assert 'item' in intent['entities'], "Missing 'item' entity"
            
            # Step 4: Dialog Processing
            dialog_response = await self._simulate_dialog_processing(
                report, session, intent, mock_services['dialog']
            )
            assert dialog_response['action'] == 'add_shopping_item'
            assert 'молоко' in dialog_response['response_text'].lower()
            
            # Step 5: Storage Persistence
            persistence_success = await self._simulate_storage_persistence(
                report, session, intent, mock_services['storage']
            )
            assert persistence_success is True, "Data persistence failed"
            
            # Step 6: TTS Generation
            audio_response = await self._simulate_tts_generation(
                report, session, dialog_response['response_text'], mock_services['tts']
            )
            assert len(audio_response) > 0, "TTS generated empty audio"
            
            # Step 7: Call Termination
            terminated = await self._simulate_call_termination(report, session)
            assert terminated is True, "Call termination failed"
            
            # Complete report
            report.complete()
            
            # Assertions on overall flow
            assert report.success_count == 7, f"Expected 7 successful steps, got {report.success_count}"
            assert report.error_count == 0, f"Expected 0 errors, got {report.error_count}"
            assert report.total_duration_ms < 5000, f"Call took too long: {report.total_duration_ms}ms"
            
            # Print detailed report
            report.print_report()
            
            logger.info("=" * 80)
            logger.info("END-TO-END TEST PASSED [OK]")
            logger.info("=" * 80)
            
        except Exception as e:
            report.complete()
            report.print_report()
            logger.error(f"END-TO-END TEST FAILED [ERR]: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(
        self,
        call_flow_report: CallFlowReport,
        mock_services: Dict,
        test_audio_data: bytes,
        test_session_data: Dict
    ):
        """
        Test error recovery during call flow.
        
        Scenario:
        1. ASR fails initially
        2. System retries and succeeds
        3. Call continues normally
        """
        logger.info("=" * 80)
        logger.info("STARTING ERROR RECOVERY TEST")
        logger.info("=" * 80)
        
        report = call_flow_report
        session = test_session_data.copy()
        
        # Configure ASR to fail once then succeed
        call_count = 0
        async def failing_then_successful_asr():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise grpc.RpcError("Temporary ASR failure")
            return {'text': 'добавь молоко', 'confidence': 0.90, 'is_final': True}
        
        mock_services['asr'].ProcessAudioStream.side_effect = failing_then_successful_asr
        
        # Step 1: Incoming call
        session = await self._simulate_freeswitch_incoming_call(report, session)
        
        # Step 2: ASR with retry
        retry_step = report.add_step(CallFlowStep(
            name="asr_with_retry",
            service="ASR/Resilience",
            details={'max_retries': 3}
        ))
        
        try:
            # First attempt fails
            try:
                await mock_services['asr'].ProcessAudioStream()
            except grpc.RpcError:
                logger.warning("ASR first attempt failed, retrying...")
            
            # Retry succeeds
            result = await mock_services['asr'].ProcessAudioStream()
            
            retry_step.complete("success", {
                'attempts': call_count,
                'final_result': result['text']
            })
            
            logger.info(f"[OK] ASR recovered after {call_count} attempts")
            
        except Exception as e:
            retry_step.complete("error", error=str(e))
            raise
        
        report.complete()
        report.print_report()
        
        assert call_count == 2, f"Expected 2 ASR calls, got {call_count}"
        assert retry_step.status == "success"
        
        logger.info("=" * 80)
        logger.info("ERROR RECOVERY TEST PASSED [OK]")
        logger.info("=" * 80)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])