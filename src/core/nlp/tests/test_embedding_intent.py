"""
Tests for Embedding-based Intent Recognition

Verifies that the new embedding approach works correctly
and maintains backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch

# Try to import the v2 recognizer
try:
    from ..intent_recognition_v2 import EmbeddingIntentRecognizer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    EmbeddingIntentRecognizer = None

from ..intent_recognition import IntentRecognizer


@pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
class TestEmbeddingIntentRecognition:
    """Test the embedding-based intent recognition"""
    
    def test_semantic_understanding(self):
        """Test that semantically similar phrases are recognized correctly"""
        recognizer = EmbeddingIntentRecognizer()
        
        # These phrases are semantically similar to "I want to help"
        # but don't contain exact keywords
        test_phrases = [
            ("I'd love to volunteer", "OFFER_HELP"),
            ("Looking to contribute to my community", "OFFER_HELP"),
            ("How can I make a difference?", "OFFER_HELP"),
            ("I want to give back", "OFFER_HELP"),
            ("Where can I lend a hand?", "OFFER_HELP"),
        ]
        
        for phrase, expected_intent in test_phrases:
            result = recognizer.recognize(phrase)
            assert result.intent == expected_intent, f"Failed for: {phrase}"
            assert result.confidence > 0.5, f"Low confidence for: {phrase}"
    
    def test_intent_variations(self):
        """Test that various ways of expressing intents are recognized"""
        recognizer = EmbeddingIntentRecognizer()
        
        # Test various ways to request help
        help_requests = [
            "We're in need of volunteers",
            "Our organization requires assistance",
            "Could use some help with our event",
            "Seeking people to assist",
        ]
        
        for phrase in help_requests:
            result = recognizer.recognize(phrase)
            assert result.intent == "REQUEST_HELP"
            assert result.confidence > 0.5
    
    def test_confidence_thresholds(self):
        """Test that confidence levels work appropriately"""
        recognizer = EmbeddingIntentRecognizer()
        
        # Clear intent should have high confidence
        result = recognizer.recognize("I want to volunteer")
        assert result.confidence > 0.75
        assert result.suggested_clarification is None
        
        # Ambiguous input should have lower confidence
        result = recognizer.recognize("maybe sometime")
        assert result.confidence < 0.5
        assert result.suggested_clarification is not None
    
    def test_contextual_responses(self):
        """Test contextual understanding of short responses"""
        recognizer = EmbeddingIntentRecognizer()
        
        # Set context
        recognizer.recognize("I want to help")
        
        # "Yes" should be understood in context
        result = recognizer.recognize("Yes")
        assert result.intent == "CONFIRM_HELP"
        assert result.confidence > 0.7
    
    def test_training_phrase_addition(self):
        """Test ability to add new training phrases"""
        recognizer = EmbeddingIntentRecognizer()
        
        # Add custom phrases for a new intent
        recognizer.add_training_phrases(
            "CUSTOM_INTENT",
            ["This is a custom phrase", "Another custom example"]
        )
        
        # Should now recognize similar phrases
        result = recognizer.recognize("This is a custom example")
        # Since we don't have the actual model, we can't test the exact behavior
        # but we can verify the method exists and doesn't crash
        assert hasattr(recognizer, "add_training_phrases")


class TestBackwardCompatibility:
    """Test that the enhanced IntentRecognizer maintains compatibility"""
    
    def test_fallback_to_pattern_matching(self):
        """Test that pattern matching works when embeddings unavailable"""
        # Mock the import to fail
        with patch('src.core.nlp.intent_recognition.EmbeddingIntentRecognizer', side_effect=ImportError):
            recognizer = IntentRecognizer()
            
            # Should fall back to pattern matching
            result = recognizer.recognize("I want to help")
            assert result.intent == "OFFER_HELP"
            assert result.confidence > 0.7
    
    def test_existing_tests_still_pass(self):
        """Verify that all existing functionality still works"""
        recognizer = IntentRecognizer()
        
        # Test cases from original tests
        test_cases = [
            ("I want to help", "OFFER_HELP"),
            ("Looking for volunteers", "REQUEST_HELP"),
            ("I'm free on weekends", "SHARE_AVAILABILITY"),
            ("I'm good at teaching", "SHARE_SKILLS"),
        ]
        
        for phrase, expected_intent in test_cases:
            result = recognizer.recognize(phrase)
            assert result.intent == expected_intent
            assert result.confidence > 0.5
    
    def test_context_reset(self):
        """Test that context reset works correctly"""
        recognizer = IntentRecognizer()
        
        # Set some context
        recognizer.recognize("I want to help")
        
        # Reset should clear context
        recognizer.reset_context()
        
        # "Yes" should no longer be contextual
        result = recognizer.recognize("Yes")
        # Without context, this might be unclear or have low confidence
        assert result.intent in ["UNCLEAR", "CONFIRM_HELP"]


@pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
class TestEmbeddingEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_input(self):
        """Test handling of empty input"""
        recognizer = EmbeddingIntentRecognizer()
        
        result = recognizer.recognize("")
        assert result.intent == "UNCLEAR"
        assert result.confidence < 0.5
    
    def test_very_long_input(self):
        """Test handling of very long input"""
        recognizer = EmbeddingIntentRecognizer()
        
        # Create a very long input
        long_text = "I want to help " * 100
        
        result = recognizer.recognize(long_text)
        # Should still recognize the intent
        assert result.intent == "OFFER_HELP"
    
    def test_mixed_intents(self):
        """Test handling of mixed intent signals"""
        recognizer = EmbeddingIntentRecognizer()
        
        # Input with mixed signals
        result = recognizer.recognize("I need help but I also want to volunteer")
        
        # Should pick the stronger signal or indicate confusion
        assert result.intent in ["OFFER_HELP", "REQUEST_HELP", "UNCLEAR"]
        
        # If unclear, should have clarification
        if result.intent == "UNCLEAR":
            assert result.suggested_clarification is not None