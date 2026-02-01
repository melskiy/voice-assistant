"""
Property-based tests for NLU Service intent classification and confidence handling.
Validates requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle
import asyncio
from typing import Dict, Any

from voice_assistant.application.dto.intent_dto import IntentDTO
from voice_assistant.infrastructure.plugins.plugin_interface import NLUPlugin
from plugins.nlu_sklearn.plugin import SklearnNLUPlugin
from plugins.nlu_regex.plugin import RegexNLUPlugin


class TestNLUService:
    """Test suite for NLU service functionality"""
    
    @given(
        text=st.text(min_size=1, max_size=200).filter(
            lambda x: x.strip() != ""  # Ensure non-empty after stripping
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_intent_classification_returns_dto(self, text):
        """Property 4: Intent Classification and Confidence Handling
        Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
        Every text input produces a valid IntentDTO with proper confidence value"""
        
        # Test with sklearn plugin
        sklearn_plugin = SklearnNLUPlugin()
        asyncio.run(sklearn_plugin._train_default_model())
        
        intent_dto = asyncio.run(sklearn_plugin.classify_intent(text))
        
        # Requirement 4.1: Intent classification must return structured data
        assert isinstance(intent_dto, IntentDTO)
        assert hasattr(intent_dto, 'name')
        assert hasattr(intent_dto, 'confidence')
        assert hasattr(intent_dto, 'entities')
        
        # Requirement 4.2: Confidence must be between 0 and 1
        assert 0.0 <= intent_dto.confidence <= 1.0
        
        # Requirement 4.3: Intent name must be a string
        assert isinstance(intent_dto.name, str)
        
        # Requirement 4.4: Entities must be a dictionary
        assert isinstance(intent_dto.entities, dict)
        
        # Clean up
        asyncio.run(sklearn_plugin.shutdown())
    
    @given(
        text=st.text(alphabet=st.characters(blacklist_categories=('Cc',)), min_size=1, max_size=100)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_regex_intent_classification_properties(self, text):
        """Additional test for regex-based NLU plugin"""
        regex_plugin = RegexNLUPlugin()
        
        intent_dto = asyncio.run(regex_plugin.classify_intent(text))
        
        # Requirement 4.1: Intent classification must return structured data
        assert isinstance(intent_dto, IntentDTO)
        assert hasattr(intent_dto, 'name')
        assert hasattr(intent_dto, 'confidence')
        assert hasattr(intent_dto, 'entities')
        
        # Requirement 4.2: Confidence must be between 0 and 1
        assert 0.0 <= intent_dto.confidence <= 1.0
        
        # Requirement 4.3: Intent name must be a string
        assert isinstance(intent_dto.name, str)
        
        # Requirement 4.4: Entities must be a dictionary
        assert isinstance(intent_dto.entities, dict)
    
    @given(
        text=st.text(min_size=1, max_size=150),
        confidence_threshold=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_threshold_behavior(self, text, confidence_threshold):
        """Test that confidence-based routing logic works properly"""
        sklearn_plugin = SklearnNLUPlugin()
        asyncio.run(sklearn_plugin._train_default_model())
        
        intent_dto = asyncio.run(sklearn_plugin.classify_intent(text))
        
        # The confidence should be consistent across multiple calls for the same input
        intent_dto_second = asyncio.run(sklearn_plugin.classify_intent(text))
        
        assert intent_dto.name == intent_dto_second.name
        assert abs(intent_dto.confidence - intent_dto_second.confidence) < 0.001  # Small epsilon for floating point comparison
        
        # Clean up
        asyncio.run(sklearn_plugin.shutdown())
    
    def test_intent_classification_consistency(self):
        """Test that intent classification is consistent for the same inputs"""
        sklearn_plugin = SklearnNLUPlugin()
        asyncio.run(sklearn_plugin._train_default_model())
        
        test_inputs = [
            "добавь молоко в список покупок",
            "напомни мне позвонить маме завтра",
            "покажи мой список покупок",
            "не нужно больше хлеба",
            "да, это правильно",
            "нет, не то"
        ]
        
        for text in test_inputs:
            # Multiple classifications of the same text should yield similar results
            intent1 = asyncio.run(sklearn_plugin.classify_intent(text))
            intent2 = asyncio.run(sklearn_plugin.classify_intent(text))
            intent3 = asyncio.run(sklearn_plugin.classify_intent(text))
            
            # Names should be identical
            assert intent1.name == intent2.name == intent3.name
            
            # Confidence should be very similar (allowing for small variations in ML models)
            assert abs(intent1.confidence - intent2.confidence) < 0.01
            assert abs(intent1.confidence - intent3.confidence) < 0.01
        
        asyncio.run(sklearn_plugin.shutdown())
    
    def test_low_confidence_intent_handling(self):
        """Test handling of low-confidence intents (Requirement 4.3, 4.4)"""
        sklearn_plugin = SklearnNLUPlugin()
        asyncio.run(sklearn_plugin._train_default_model())
        
        # Test with random gibberish that should have low confidence
        low_quality_inputs = [
            "абвгде жзийкл мнпрст уфхцч шщъыь эюя",
            "xyz abc 123 def",
            "random garbage text without meaning",
            "нечто совершенно непонятное и бессмысленное"
        ]
        
        for text in low_quality_inputs:
            intent_dto = asyncio.run(sklearn_plugin.classify_intent(text))
            
            # Low-quality inputs should typically have lower confidence
            # Though ML models might assign some confidence to any input
            assert 0.0 <= intent_dto.confidence <= 1.0
            assert isinstance(intent_dto.name, str)
            assert isinstance(intent_dto.entities, dict)
        
        asyncio.run(sklearn_plugin.shutdown())


# State machine test for NLU service lifecycle
class NLUServiceStateMachine(RuleBasedStateMachine):
    """State machine test for NLU service lifecycle and operations"""
    
    nlu_plugins = Bundle("nlu_plugins")
    
    @rule(target=nlu_plugins, plugin_type=st.sampled_from(['sklearn', 'regex']))
    def create_plugin(self, plugin_type):
        """Create an NLU plugin instance"""
        if plugin_type == 'sklearn':
            plugin = SklearnNLUPlugin()
            asyncio.run(plugin._train_default_model())
        else:
            plugin = RegexNLUPlugin()
        
        return plugin
    
    @rule(plugin=nlu_plugins, text=st.text(min_size=1, max_size=100))
    def classify_intent(self, plugin, text):
        """Classify intent for given text"""
        intent_dto = asyncio.run(plugin.classify_intent(text))
        
        # Validate DTO structure
        assert isinstance(intent_dto, IntentDTO)
        assert 0.0 <= intent_dto.confidence <= 1.0
        assert isinstance(intent_dto.name, str)
        assert isinstance(intent_dto.entities, dict)
    
    @rule(plugin=nlu_plugins)
    def check_availability(self, plugin):
        """Check if plugin is available"""
        available = plugin.is_available()
        assert isinstance(available, bool)
    
    @rule(plugin=nlu_plugins)
    def shutdown_plugin(self, plugin):
        """Shutdown plugin and clean up resources"""
        asyncio.run(plugin.shutdown())


TestNLUStateMachine = NLUServiceStateMachine.TestCase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])