import spacy
from typing import Dict, Any, List
from enum import Enum
from rodi import Container
import re

from voice_assistant.infrastructure.plugins.plugin_interface import BasePlugin, NLUPlugin
from voice_assistant.application.dto.intent_dto import IntentDTO


class IntentType(Enum):
    ADD_SHOPPING_ITEM = "ADD_SHOPPING_ITEM"
    REMOVE_SHOPPING_ITEM = "REMOVE_SHOPPING_ITEM"
    GET_SHOPPING_LIST = "GET_SHOPPING_LIST"
    CREATE_REMINDER = "CREATE_REMINDER"
    GET_REMINDERS = "GET_REMINDERS"
    CONFIRM_YES = "CONFIRM_YES"
    CONFIRM_NO = "CONFIRM_NO"
    UNKNOWN = "UNKNOWN"


class SpacyNLUPlugin(BasePlugin):
    """spaCy-based NLU plugin implementation for Russian language processing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.nlp = None
        self.is_loaded = False
        self.language = "ru"
        self.intent_patterns = {}
        self.entity_patterns = {}
        self.trained_intents = set()
        
        # Initialize with config if provided
        if config:
            self._initialize_sync(config)
    
    @classmethod
    def get_id(cls) -> str:
        return "nlu.spacy"
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "default": "ru",
                    "description": "Language code for spaCy model"
                },
                "model_path": {
                    "type": "string",
                    "description": "Path to custom spaCy model"
                },
                "use_default_model": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to use default Russian model"
                }
            },
            "required": []
        }
    
    @classmethod
    def register_dependencies(cls, container: Container, config: Dict[str, Any]) -> None:
        """Register plugin dependencies in IoC container"""
        try:
            # Initialize spaCy model
            model_path = config.get("model_path")
            use_default = config.get("use_default_model", True)
            
            if model_path:
                # Load custom model
                nlp = spacy.load(model_path)
            elif use_default:
                # Try to load Russian model
                try:
                    nlp = spacy.load("ru_core_news_sm")
                except OSError:
                    # If Russian model not found, warn but continue
                    print("Russian spaCy model not found. Install with: python -m spacy download ru_core_news_sm")
                    # Fallback to basic initialization
                    nlp = None
            else:
                nlp = None
            
            # Register the spaCy model
            container.add_singleton(spacy.Language, lambda: nlp)
            
            # Register NLU service interface
            container.add_singleton(NLUPlugin, lambda: cls.create_from_container(container, config))
            
            print("Registered spaCy NLU components")
            
        except Exception as e:
            print(f"Failed to register spaCy NLU dependencies: {e}")
    
    @classmethod
    def create_from_container(cls, container: Container, config: Dict[str, Any]):
        """Create instance using dependencies from IoC container"""
        try:
            nlp = container.resolve(spacy.Language)
            
            instance = cls()
            instance.nlp = nlp
            instance.is_loaded = nlp is not None
            instance.language = config.get("language", "ru")
            
            return instance
        except Exception as e:
            print(f"Failed to create SpacyNLUPlugin from container: {e}")
            return None
    
    def _initialize_sync(self, config: Dict[str, Any]) -> None:
        """Synchronous initialization for IoC container"""
        try:
            self.language = config.get("language", "ru")
            model_path = config.get("model_path")
            use_default = config.get("use_default_model", True)
            
            if model_path:
                # Load custom model
                self.nlp = spacy.load(model_path)
                self.is_loaded = True
            elif use_default:
                # Try to load Russian model
                try:
                    self.nlp = spacy.load("ru_core_news_sm")
                    self.is_loaded = True
                except OSError:
                    print("Russian spaCy model not found. Install with: python -m spacy download ru_core_news_sm")
                    self.is_loaded = False
            else:
                self.is_loaded = False
                
        except Exception as e:
            print(f"Failed to initialize spaCy NLU: {e}")
            self.is_loaded = False
    
    def is_available(self) -> bool:
        """Check if spaCy NLU is available"""
        try:
            import spacy
            return self.is_loaded
        except ImportError:
            return False
    
    def _classify_intent_with_spacy(self, text: str) -> IntentDTO:
        """Classify intent using spaCy's NLP capabilities"""
        if not self.nlp:
            # Fallback to pattern matching if spaCy model not loaded
            return self._fallback_classify_intent(text)
        
        doc = self.nlp(text)
        
        # Extract tokens and their lemmas
        tokens = [token.text.lower() for token in doc if not token.is_stop and not token.is_punct]
        lemmas = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]
        
        # Look for intent-indicating keywords
        token_text = ' '.join(tokens)
        lemma_text = ' '.join(lemmas)
        full_text_lower = text.lower()
        
        # Shopping intent patterns
        if any(word in full_text_lower for word in ["добав", "куп", "нужн", "полож", "взять"]):
            # Extract item entity if possible
            entities = self._extract_entities_with_spacy(doc)
            confidence = 0.85
            return IntentDTO(
                name=IntentType.ADD_SHOPPING_ITEM.value,
                confidence=confidence,
                entities=entities
            )
        
        elif any(word in full_text_lower for word in ["удал", "убрать", "вычерк", "не нужн", "не над"]):
            entities = self._extract_entities_with_spacy(doc)
            confidence = 0.80
            return IntentDTO(
                name=IntentType.REMOVE_SHOPPING_ITEM.value,
                confidence=confidence,
                entities=entities
            )
        
        elif any(word in full_text_lower for word in ["покаж", "список", "покупк", "перечисл", "назов"]):
            entities = self._extract_entities_with_spacy(doc)
            confidence = 0.75
            return IntentDTO(
                name=IntentType.GET_SHOPPING_LIST.value,
                confidence=confidence,
                entities=entities
            )
        
        # Reminder intent patterns
        elif any(word in full_text_lower for word in ["напомн", "напоминан", "запиш", "установ"]):
            entities = self._extract_entities_with_spacy(doc)
            confidence = 0.80
            return IntentDTO(
                name=IntentType.CREATE_REMINDER.value,
                confidence=confidence,
                entities=entities
            )
        
        elif any(word in full_text_lower for word in ["напоминан", "уведомлен", "напомни"]):
            entities = self._extract_entities_with_spacy(doc)
            confidence = 0.70
            return IntentDTO(
                name=IntentType.GET_REMINDERS.value,
                confidence=confidence,
                entities=entities
            )
        
        # Confirmation patterns
        elif any(word in full_text_lower for word in ["да", "ага", "верно", "правильно", "угу", "се"]):
            confidence = 0.95
            return IntentDTO(
                name=IntentType.CONFIRM_YES.value,
                confidence=confidence,
                entities={}
            )
        
        elif any(word in full_text_lower for word in ["нет", "не", "отмен", "не хочу"]):
            confidence = 0.90
            return IntentDTO(
                name=IntentType.CONFIRM_NO.value,
                confidence=confidence,
                entities={}
            )
        
        # If no clear intent found, return unknown
        return IntentDTO(
            name=IntentType.UNKNOWN.value,
            confidence=0.30,
            entities={}
        )
    
    def _extract_entities_with_spacy(self, doc) -> Dict[str, Any]:
        """Extract named entities using spaCy"""
        entities = {}
        
        if not self.nlp:
            return entities
        
        # Extract named entities recognized by spaCy
        for ent in doc.ents:
            if ent.label_ in ['DATE', 'TIME', 'CARDINAL', 'MONEY', 'PERCENT']:
                entities[ent.label_.lower()] = ent.text
        
        # Look for specific Russian patterns manually if needed
        text = doc.text.lower()
        
        # Extract potential items from shopping context
        shopping_keywords = ["молоко", "хлеб", "яйца", "сыр", "масло", "творог", "кефир"]
        for item in shopping_keywords:
            if item in text:
                if 'item' not in entities:
                    entities['item'] = item
        
        # Extract numbers (potential quantities)
        numbers = re.findall(r'\d+', doc.text)
        if numbers:
            entities['quantity'] = int(numbers[0])
        
        # Extract time expressions
        time_patterns = [
            r'(\d{1,2}[:.]\d{2})',  # Times like 10:30
            r'(утром|днем|вечером|ночью)',  # Time of day
            r'(сегодня|завтра|послезавтра)',  # Days
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if 'time' not in entities:
                    entities['time'] = matches[0]
                break
        
        return entities
    
    def _fallback_classify_intent(self, text: str) -> IntentDTO:
        """Fallback intent classification using pattern matching when spaCy is not available"""
        text_lower = text.lower()
        
        # Shopping intent patterns
        if any(word in text_lower for word in ["добавь", "добавить", "купить", "нужно", "положить", "взять"]):
            # Extract item if mentioned
            entities = {}
            shopping_items = ["молоко", "хлеб", "яйца", "сыр", "масло", "творог", "кефир"]
            for item in shopping_items:
                if item in text_lower:
                    entities['item'] = item
                    break
            
            # Extract quantity
            numbers = re.findall(r'\d+', text)
            if numbers:
                entities['quantity'] = int(numbers[0])
            
            confidence = 0.70
            return IntentDTO(
                name=IntentType.ADD_SHOPPING_ITEM.value,
                confidence=confidence,
                entities=entities
            )
        
        elif any(word in text_lower for word in ["удали", "удалить", "убрать", "вычеркнуть", "не нужно", "не надо"]):
            confidence = 0.65
            return IntentDTO(
                name=IntentType.REMOVE_SHOPPING_ITEM.value,
                confidence=confidence,
                entities={}
            )
        
        elif any(word in text_lower for word in ["покажи", "показать", "список", "покупки", "перечисли", "назови"]):
            confidence = 0.60
            return IntentDTO(
                name=IntentType.GET_SHOPPING_LIST.value,
                confidence=confidence,
                entities={}
            )
        
        # Reminder intent patterns
        elif any(word in text_lower for word in ["напомни", "напомнить", "запиши", "установи"]):
            entities = {}
            # Extract time reference if present
            time_refs = ["сегодня", "завтра", "послезавтра", "через час"]
            for ref in time_refs:
                if ref in text_lower:
                    entities['time_reference'] = ref
                    break
            
            confidence = 0.70
            return IntentDTO(
                name=IntentType.CREATE_REMINDER.value,
                confidence=confidence,
                entities=entities
            )
        
        elif any(word in text_lower for word in ["напоминания", "уведомления", "напомни мне"]):
            confidence = 0.60
            return IntentDTO(
                name=IntentType.GET_REMINDERS.value,
                confidence=confidence,
                entities={}
            )
        
        # Confirmation patterns
        elif any(word in text_lower for word in ["да", "ага", "верно", "правильно", "угу", "се"]):
            confidence = 0.90
            return IntentDTO(
                name=IntentType.CONFIRM_YES.value,
                confidence=confidence,
                entities={}
            )
        
        elif any(word in text_lower for word in ["нет", "не", "отмена", "не хочу"]):
            confidence = 0.85
            return IntentDTO(
                name=IntentType.CONFIRM_NO.value,
                confidence=confidence,
                entities={}
            )
        
        # Unknown intent
        return IntentDTO(
            name=IntentType.UNKNOWN.value,
            confidence=0.25,
            entities={}
        )
    
    async def classify_intent(self, text: str) -> IntentDTO:
        """Classify intent from text using spaCy"""
        try:
            return self._classify_intent_with_spacy(text)
        except Exception as e:
            print(f"Error in spaCy intent classification: {e}")
            # Return fallback classification
            return self._fallback_classify_intent(text)
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text"""
        if not self.nlp:
            return {}
        
        doc = self.nlp(text)
        return self._extract_entities_with_spacy(doc)
    
    async def process_text(self, text: str) -> IntentDTO:
        """Process text to extract intent and entities"""
        return await self.classify_intent(text)
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        try:
            self._initialize_sync(config)
            return True
        except Exception as e:
            print(f"Failed to initialize spaCy NLU: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Clean up resources"""
        # Clear the NLP model to free memory
        self.nlp = None
        self.is_loaded = False