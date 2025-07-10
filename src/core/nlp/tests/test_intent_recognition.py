"""
Intent Recognition Tests

Start here. Make these pass first.
"""

import pytest
from unittest.mock import Mock

from ..intent_recognition import IntentRecognizer


class TestBasicIntents:
    """Basic intent recognition - the foundation of everything"""
    
    def test_help_intent(self):
        """User wants to help their community"""
        recognizer = IntentRecognizer()
        
        # Multiple ways people express wanting to help
        help_phrases = [
            "I want to help",
            "How can I volunteer?",
            "I'd like to contribute to my community",
            "I have time to help out",
            "What needs doing in my neighborhood?",
        ]
        
        for phrase in help_phrases:
            result = recognizer.recognize(phrase)
            assert result.intent == "OFFER_HELP"
            assert result.confidence > 0.7
    
    def test_need_help_intent(self):
        """Community member needs assistance"""
        recognizer = IntentRecognizer()
        
        need_phrases = [
            "I need help with my garden",
            "Looking for volunteers this weekend",
            "We need people to help at the food bank",
            "Seeking tutors for local kids",
        ]
        
        for phrase in need_phrases:
            result = recognizer.recognize(phrase)
            assert result.intent == "REQUEST_HELP"
            assert result.confidence > 0.7
    
    def test_availability_intent(self):
        """User shares when they're available"""
        recognizer = IntentRecognizer()
        
        availability_phrases = [
            "I'm free on weekends",
            "I have Tuesday evenings available",
            "I can help Saturday mornings",
        ]
        
        for phrase in availability_phrases:
            result = recognizer.recognize(phrase)
            assert result.intent == "SHARE_AVAILABILITY"
            assert result.confidence > 0.7
    
    def test_skill_sharing_intent(self):
        """User shares their skills"""
        recognizer = IntentRecognizer()
        
        skill_phrases = [
            "I'm good at teaching",
            "I know how to code",
            "I'm a master gardener",
            "I can help with math tutoring",
        ]
        
        for phrase in skill_phrases:
            result = recognizer.recognize(phrase)
            assert result.intent == "SHARE_SKILLS"
            assert result.confidence > 0.7


class TestIntentContext:
    """Intent recognition with context awareness"""
    
    def test_contextual_intent(self):
        """Intent changes based on conversation context"""
        recognizer = IntentRecognizer()
        
        # First message establishes context
        recognizer.recognize("I want to help")
        
        # "Yes" in this context means confirming help
        result = recognizer.recognize("Yes")
        assert result.intent == "CONFIRM_HELP"
        
        # New conversation
        recognizer.reset_context()
        recognizer.recognize("I need help")
        
        # Same "Yes" now means something different  
        result = recognizer.recognize("Yes")
        assert result.intent == "CONFIRM_INTEREST"


class TestEdgeCases:
    """Handle unclear or ambiguous inputs gracefully"""
    
    def test_unclear_intent(self):
        """When we're not sure, we should ask"""
        recognizer = IntentRecognizer()
        
        unclear_phrases = [
            "Hello",
            "Hmm",
            "Maybe",
            "I don't know",
        ]
        
        for phrase in unclear_phrases:
            result = recognizer.recognize(phrase)
            assert result.intent == "UNCLEAR"
            assert result.confidence < 0.5
            assert result.suggested_clarification is not None


# Run with: pytest -xvs test_intent_recognition.py