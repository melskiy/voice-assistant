"""
Dialog Service gRPC Servicer.

Implements the gRPC interface for Dialog Service.
Delegates business logic to use cases.
"""
import logging
from typing import Dict, Any
from datetime import datetime

import grpc

from ...infrastructure.grpc.generated import dialog_pb2, dialog_pb2_grpc
from ...domain.entities.dialog_session import DialogSession, DialogTurn
from ...application.use_cases.dialog_use_cases import (
    ProcessIntentUseCase,
    HandleConfirmationUseCase,
    GetDialogStateUseCase,
    ResetDialogUseCase
)


logger = logging.getLogger(__name__)


class DialogServiceServicer(dialog_pb2_grpc.DialogServiceServicer):
    """
    gRPC servicer implementation for Dialog Service.
    
    Translates gRPC requests to use case calls and responses back to protobuf.
    """
    
    def __init__(
        self,
        process_intent_use_case: ProcessIntentUseCase,
        handle_confirmation_use_case: HandleConfirmationUseCase,
        get_dialog_state_use_case: GetDialogStateUseCase,
        reset_dialog_use_case: ResetDialogUseCase
    ):
        self.process_intent_use_case = process_intent_use_case
        self.handle_confirmation_use_case = handle_confirmation_use_case
        self.get_dialog_state_use_case = get_dialog_state_use_case
        self.reset_dialog_use_case = reset_dialog_use_case
        logger.info("DialogServiceServicer initialized")
    
    async def ProcessIntent(self, request, context):
        """Process an intent and generate an appropriate response."""
        try:
            logger.info(f"Processing intent for session {request.session_id}: {request.intent.name}")
            
            # Convert protobuf entities to dict
            entities = dict(request.intent.entities)
            
            # Process intent through use case
            response_text, action, requires_confirmation, session_complete = \
                await self.process_intent_use_case.execute(
                    session_id=request.session_id,
                    intent_name=request.intent.name,
                    entities=entities,
                    confidence=request.intent.confidence,
                    raw_text=request.intent.raw_text
                )
            
            logger.info(f"Generated response: {response_text}")
            
            return dialog_pb2.DialogResponse(
                session_id=request.session_id,
                response_text=response_text,
                action=action,
                updated_context=entities,
                requires_confirmation=requires_confirmation,
                session_complete=session_complete
            )
            
        except Exception as e:
            logger.error(f"Error processing intent: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return dialog_pb2.DialogResponse(
                session_id=request.session_id,
                response_text="Извините, произошла ошибка при обработке запроса",
                action="error",
                updated_context={},
                requires_confirmation=False,
                session_complete=False
            )
    
    async def HandleConfirmation(self, request, context):
        """Handle user confirmation responses."""
        try:
            logger.info(f"Handling confirmation for session {request.session_id}: {request.response}")
            
            response_text, action, requires_confirmation, session_complete = \
                await self.handle_confirmation_use_case.execute(
                    session_id=request.session_id,
                    response=request.response
                )
            
            return dialog_pb2.DialogResponse(
                session_id=request.session_id,
                response_text=response_text,
                action=action,
                updated_context={},
                requires_confirmation=requires_confirmation,
                session_complete=session_complete
            )
            
        except Exception as e:
            logger.error(f"Error handling confirmation: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return dialog_pb2.DialogResponse(
                session_id=request.session_id,
                response_text="Извините, произошла ошибка при обработке подтверждения",
                action="error",
                updated_context={},
                requires_confirmation=False,
                session_complete=False
            )
    
    async def GetDialogState(self, request, context):
        """Get the current dialog state for a session."""
        try:
            session = await self.get_dialog_state_use_case.execute(request.session_id)
            
            # Convert to protobuf
            pb_dialog_state = dialog_pb2.DialogState(
                session_id=session.session_id,
                current_intent=session.current_intent
            )
            
            # Add conversation history
            for turn in session.conversation_history:
                pb_turn = dialog_pb2.DialogTurn(
                    user_input=turn.user_input,
                    system_response=turn.system_response,
                    intent_name=turn.intent_name,
                    timestamp_ms=turn.timestamp_ms,
                    confidence=turn.confidence
                )
                # Add entities
                for key, value in turn.entities.items():
                    pb_turn.entities[key] = value
                pb_dialog_state.conversation_history.append(pb_turn)
            
            # Add pending confirmations
            pb_dialog_state.pending_confirmations.extend(session.pending_confirmations)
            
            # Add context variables
            for key, value in session.context_variables.items():
                pb_dialog_state.context_variables[key] = value
            
            return pb_dialog_state
            
        except Exception as e:
            logger.error(f"Error getting dialog state: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return dialog_pb2.DialogState()
    
    async def ResetSession(self, request, context):
        """Reset a dialog session."""
        try:
            success = await self.reset_dialog_use_case.execute(request.session_id)
            return dialog_pb2.ResetSessionResponse(
                session_id=request.session_id,
                success=success
            )
        except Exception as e:
            logger.error(f"Error resetting session: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return dialog_pb2.ResetSessionResponse(
                session_id=request.session_id,
                success=False
            )
