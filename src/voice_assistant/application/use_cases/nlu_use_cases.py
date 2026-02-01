"""
NLU Use Cases for NLU Service.

User goal: Extract intent and entities from text.
Success guarantee: Returns intent classification with confidence.
Side effects: None (stateless operation).
"""
from typing import Optional, List

from ...application.dto.intent_dto import IntentDTO
from ...infrastructure.plugins.plugin_interface import NLUPlugin


class ExtractIntentUseCase:
    """
    Use case for extracting intent from text.
    
    Uses NLU plugin to classify intent and extract entities.
    """
    
    def __init__(
        self,
        nlu_plugin: NLUPlugin,
        confidence_threshold: float = 0.7
    ):
        self.nlu_plugin = nlu_plugin
        self.confidence_threshold = confidence_threshold
    
    async def execute(self, text: str, session_id: str) -> Optional[IntentDTO]:
        """
        Extract intent from text.
        
        Args:
            text: Input text to classify
            session_id: Session identifier
            
        Returns:
            IntentDTO or None if extraction failed
        """
        if not self.nlu_plugin:
            return None
        
        try:
            intent_dto = await self.nlu_plugin.process_text(text)
            return intent_dto
        except Exception as e:
            return None
    
    def get_supported_intents(self) -> List[str]:
        """
        Get list of supported intents.
        
        Returns:
            List of intent names
        """
        return [
            "ADD_SHOPPING_ITEM",
            "REMOVE_SHOPPING_ITEM",
            "GET_SHOPPING_LIST",
            "CREATE_REMINDER",
            "GET_REMINDERS",
            "CONFIRM_YES",
            "CONFIRM_NO",
            "HELP",
            "UNKNOWN"
        ]


class ProcessConfidenceUseCase:
    """
    Use case for processing confidence scores.
    
    Categorizes confidence and determines routing decisions.
    """
    
    def __init__(
        self,
        high_threshold: float = 0.8,
        medium_threshold: float = 0.6,
        low_threshold: float = 0.4
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.low_threshold = low_threshold
    
    def execute(self, intent: IntentDTO) -> tuple[IntentDTO, str, str]:
        """
        Process intent confidence.
        
        Args:
            intent: Intent to process
            
        Returns:
            Tuple of (processed_intent, confidence_category, routing_decision)
        """
        confidence = intent.confidence
        
        if confidence >= self.high_threshold:
            category = "HIGH"
            routing = "PROCEED"
        elif confidence >= self.medium_threshold:
            category = "MEDIUM"
            routing = "CONFIRM"
        elif confidence >= self.low_threshold:
            category = "LOW"
            routing = "RETRY"
        else:
            category = "CRITICAL"
            routing = "ESCALATE"
        
        return intent, category, routing
