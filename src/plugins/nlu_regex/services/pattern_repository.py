"""
Pattern repository implementation for Regex NLU.

Contains the concrete implementations of pattern matching and entity extraction.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..interfaces import IIntentPattern, IEntityExtractor, IPatternRepository


@dataclass
class IntentPattern(IIntentPattern):
    """Concrete implementation of intent pattern."""
    
    intent_name: str
    patterns: List[str]
    case_sensitive: bool = False
    
    def __post_init__(self):
        """Compile regex patterns."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._compiled = [re.compile(p, flags) for p in self.patterns]
    
    @property
    def intent_name(self) -> str:
        return self._intent_name
    
    @intent_name.setter
    def intent_name(self, value: str):
        self._intent_name = value
    
    def matches(self, text: str) -> bool:
        """Check if text matches any pattern."""
        for pattern in self._compiled:
            if pattern.search(text):
                return True
        return False


class RegexEntityExtractor(IEntityExtractor):
    """
    Entity extractor using regex patterns.
    
    Extracts common entities like items, dates, times, etc.
    """
    
    def __init__(self, language: str = "ru"):
        """
        Initialize extractor.
        
        Args:
            language: Language code for extraction patterns
        """
        self.language = language
        self._patterns = self._load_entity_patterns()
    
    def _load_entity_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load entity extraction patterns."""
        patterns = {}
        
        if self.language == "ru":
            # Russian entity patterns
            patterns["item"] = [
                re.compile(r"(?:добавь|купи|нужен|нужна|нужно|возьми|положи)\s+(\w+)", re.IGNORECASE),
                re.compile(r"(?:в список|в покупки)\s+(\w+)", re.IGNORECASE),
            ]
            patterns["date"] = [
                re.compile(r"(?:завтра|послезавтра|сегодня|в понедельник|во вторник|в среду|в четверг|в пятницу|в субботу|в воскресенье)", re.IGNORECASE),
                re.compile(r"(\d{1,2})\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)", re.IGNORECASE),
            ]
            patterns["time"] = [
                re.compile(r"(?:в|к)\s+(\d{1,2})(?::(\d{2}))?\s*(?:утра|дня|вечера|ночи)?", re.IGNORECASE),
            ]
        else:
            # Default English patterns
            patterns["item"] = [
                re.compile(r"(?:add|buy|need|get)\s+(\w+)", re.IGNORECASE),
                re.compile(r"(?:to the list|to shopping)\s+(\w+)", re.IGNORECASE),
            ]
            patterns["date"] = [
                re.compile(r"(?:tomorrow|today|next week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)", re.IGNORECASE),
            ]
            patterns["time"] = [
                re.compile(r"(?:at|by)\s+(\d{1,2})(?::(\d{2}))?\s*(?:am|pm)?", re.IGNORECASE),
            ]
        
        return patterns
    
    def extract(self, text: str, intent: str = None) -> Dict[str, Any]:
        """
        Extract entities from text.
        
        Args:
            text: Input text
            intent: Optional intent context
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    entities[entity_type] = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    break
        
        return entities


class InMemoryPatternRepository(IPatternRepository):
    """
    In-memory pattern repository.
    
    Stores and manages intent patterns.
    """
    
    def __init__(self, language: str = "ru", case_sensitive: bool = False):
        """
        Initialize repository.
        
        Args:
            language: Language code for default patterns
            case_sensitive: Whether pattern matching is case sensitive
        """
        self.language = language
        self.case_sensitive = case_sensitive
        self._patterns: Dict[str, IntentPattern] = {}
        self._load_default_patterns()
    
    def _load_default_patterns(self) -> None:
        """Load default intent patterns."""
        if self.language == "ru":
            patterns = {
                "ADD_SHOPPING_ITEM": IntentPattern(
                    intent_name="ADD_SHOPPING_ITEM",
                    patterns=[
                        r"добавь.*в список",
                        r"купи.*",
                        r"нужен.*",
                        r"нужна.*",
                        r"возьми.*",
                        r"положи.*в список",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "REMOVE_SHOPPING_ITEM": IntentPattern(
                    intent_name="REMOVE_SHOPPING_ITEM",
                    patterns=[
                        r"удали.*из списка",
                        r"убери.*",
                        r"вычеркни.*",
                        r"не нужен.*",
                        r"не нужна.*",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "GET_SHOPPING_LIST": IntentPattern(
                    intent_name="GET_SHOPPING_LIST",
                    patterns=[
                        r"покажи список",
                        r"что в списке",
                        r"список покупок",
                        r"перечисли.*",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "CREATE_REMINDER": IntentPattern(
                    intent_name="CREATE_REMINDER",
                    patterns=[
                        r"напомни.*",
                        r"установи напоминание",
                        r"запомни.*",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "GET_REMINDERS": IntentPattern(
                    intent_name="GET_REMINDERS",
                    patterns=[
                        r"какие напоминания",
                        r"покажи напоминания",
                        r"что запланировано",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "CONFIRM_YES": IntentPattern(
                    intent_name="CONFIRM_YES",
                    patterns=[
                        r"^да$",
                        r"^да,.*",
                        r"^верно$",
                        r"^правильно$",
                        r"^так$",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "CONFIRM_NO": IntentPattern(
                    intent_name="CONFIRM_NO",
                    patterns=[
                        r"^нет$",
                        r"^нет,.*",
                        r"^не.*",
                        r"^отмена$",
                        r"^отменить$",
                    ],
                    case_sensitive=self.case_sensitive
                ),
            }
        else:
            # Default English patterns
            patterns = {
                "ADD_SHOPPING_ITEM": IntentPattern(
                    intent_name="ADD_SHOPPING_ITEM",
                    patterns=[
                        r"add.*to (the )?list",
                        r"buy.*",
                        r"need.*",
                        r"get.*",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "REMOVE_SHOPPING_ITEM": IntentPattern(
                    intent_name="REMOVE_SHOPPING_ITEM",
                    patterns=[
                        r"remove.*from (the )?list",
                        r"delete.*",
                        r"take off.*",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "GET_SHOPPING_LIST": IntentPattern(
                    intent_name="GET_SHOPPING_LIST",
                    patterns=[
                        r"show (the )?list",
                        r"what.*on (the )?list",
                        r"shopping list",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "CREATE_REMINDER": IntentPattern(
                    intent_name="CREATE_REMINDER",
                    patterns=[
                        r"remind me.*",
                        r"set a reminder.*",
                        r"remember.*",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "GET_REMINDERS": IntentPattern(
                    intent_name="GET_REMINDERS",
                    patterns=[
                        r"what.*reminders",
                        r"show.*reminders",
                        r"what.*planned",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "CONFIRM_YES": IntentPattern(
                    intent_name="CONFIRM_YES",
                    patterns=[
                        r"^yes$",
                        r"^yeah$",
                        r"^correct$",
                        r"^right$",
                    ],
                    case_sensitive=self.case_sensitive
                ),
                "CONFIRM_NO": IntentPattern(
                    intent_name="CONFIRM_NO",
                    patterns=[
                        r"^no$",
                        r"^nope$",
                        r"^incorrect$",
                        r"^cancel$",
                    ],
                    case_sensitive=self.case_sensitive
                ),
            }
        
        self._patterns = patterns
    
    def get_patterns(self, intent: str = None) -> List[IIntentPattern]:
        """
        Get patterns, optionally filtered by intent.
        
        Args:
            intent: Optional intent name to filter by
            
        Returns:
            List of intent patterns
        """
        if intent:
            pattern = self._patterns.get(intent)
            return [pattern] if pattern else []
        return list(self._patterns.values())
    
    def add_pattern(self, pattern: IIntentPattern) -> None:
        """Add a new pattern to the repository."""
        self._patterns[pattern.intent_name] = pattern
    
    def find_matching_intent(self, text: str) -> Optional[str]:
        """
        Find the first matching intent for the given text.
        
        Args:
            text: Input text to match
            
        Returns:
            Intent name if matched, None otherwise
        """
        for pattern in self._patterns.values():
            if pattern.matches(text):
                return pattern.intent_name
        return None
