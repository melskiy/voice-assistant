"""
NLU Service gRPC Servicer.

Implements the gRPC interface for NLU Service.
"""
import logging
from typing import Optional

import grpc

from ...infrastructure.grpc.generated import nlu_pb2, nlu_pb2_grpc
from ...application.use_cases.nlu_use_cases import (
    ExtractIntentUseCase,
    ProcessConfidenceUseCase
)

logger = logging.getLogger(__name__)


class NLUServiceServicer(nlu_pb2_grpc.NLUServiceServicer):
    """
    gRPC servicer implementation for NLU Service.
    """
    
    def __init__(
        self,
        extract_intent_use_case: ExtractIntentUseCase,
        process_confidence_use_case: ProcessConfidenceUseCase
    ):
        self.extract_intent_use_case = extract_intent_use_case
        self.process_confidence_use_case = process_confidence_use_case
        logger.info("NLUServiceServicer initialized")
    
    async def ExtractIntent(self, request, context):
        """Extract intent from text."""
        try:
            logger.info(f"Processing intent extraction for session {request.session_id}")
            
            # Extract intent
            intent_dto = await self.extract_intent_use_case.execute(
                text=request.text,
                session_id=request.session_id
            )
            
            if not intent_dto:
                logger.error("No NLU plugin available")
                return nlu_pb2.IntentResponse(
                    success=False,
                    error_message="No NLU plugin available",
                    intent=None
                )
            
            # Process confidence
            processed_intent, confidence_category, routing_decision = \
                self.process_confidence_use_case.execute(intent_dto)
            
            logger.debug(f"Routing decision: {routing_decision}")
            
            # Create protobuf intent
            intent = nlu_pb2.Intent(
                name=processed_intent.name,
                confidence=float(processed_intent.confidence),
                raw_text=request.text,
                session_id=request.session_id
            )
            
            # Add entities
            for key, value in processed_intent.entities.items():
                intent.entities[key] = str(value)
            
            # Add metadata
            intent.entities['confidence_category'] = confidence_category
            intent.entities['routing_decision'] = routing_decision
            
            logger.info(
                f"Intent extracted: {intent.name} with confidence {intent.confidence} "
                f"(category: {confidence_category})"
            )
            
            return nlu_pb2.IntentResponse(
                success=True,
                intent=intent,
                error_message=""
            )
            
        except Exception as e:
            logger.error(f"Error during intent extraction: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return nlu_pb2.IntentResponse(
                success=False,
                error_message=str(e),
                intent=None
            )
    
    async def GetSupportedIntents(self, request, context):
        """Get list of supported intents."""
        try:
            supported_intents = self.extract_intent_use_case.get_supported_intents()
            
            return nlu_pb2.SupportedIntentsResponse(
                intent_names=supported_intents
            )
            
        except Exception as e:
            logger.error(f"Error getting supported intents: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return nlu_pb2.SupportedIntentsResponse(
                intent_names=[]
            )
