"""
Context Tracker Tests

Test conversation context tracking and intent enhancement.
"""

import pytest
from datetime import datetime
from ..context_tracker import ContextTracker, ConversationContext, ConversationTurn
from ...nlp.nlp_processor import NLPProcessor, NLPResult
from ...nlp.intent_recognition import IntentResult
from ...nlp.entity_extraction import ExtractedEntities


class TestContextTracking:
    """Test basic context tracking functionality"""
    
    def test_add_turn(self):
        """Test adding conversation turns"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Add a turn
        nlp_result = processor.process("I want to help")
        tracker.add_turn("I want to help", nlp_result, "How can you help?")
        
        # Check context
        assert len(tracker.context.turns) == 1
        assert tracker.context.established_intent == "OFFER_HELP"
        
    def test_conversation_history(self):
        """Test maintaining conversation history"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Add multiple turns
        turns = [
            ("I want to help", "Great! What skills do you have?"),
            ("I can teach", "When are you available?"),
            ("Weekends", "Where would you like to help?"),
        ]
        
        for user_input, response in turns:
            nlp_result = processor.process(user_input)
            tracker.add_turn(user_input, nlp_result, response)
            
        # Check history
        assert len(tracker.context.turns) == 3
        recent = tracker.context.get_recent_turns(2)
        assert len(recent) == 2
        assert recent[-1].user_input == "Weekends"
        
    def test_entity_accumulation(self):
        """Test accumulating entities across turns"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Add turns with different entities
        tracker.add_turn(
            "I can teach math",
            processor.process("I can teach math"),
            "Great!"
        )
        
        tracker.add_turn(
            "I'm available Saturday mornings", 
            processor.process("I'm available Saturday mornings"),
            "Thanks!"
        )
        
        tracker.add_turn(
            "At the library",
            processor.process("At the library"),
            "Perfect!"
        )
        
        # Check accumulated entities
        entities = tracker.context.mentioned_entities
        assert "skills" in entities
        assert "teaching" in entities["skills"]
        assert "math" in entities["skills"]
        assert "times" in entities
        assert any(t["day"] == "saturday" for t in entities["times"])
        assert "locations" in entities
        assert "library" in entities["locations"]


class TestIntentEnhancement:
    """Test context-based intent enhancement"""
    
    def test_enhance_unclear_intent(self):
        """Test enhancing unclear intents from context"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Establish context
        tracker.add_turn(
            "I want to volunteer",
            processor.process("I want to volunteer"),
            "What skills do you have?"
        )
        
        # Process unclear input
        unclear_result = NLPResult(
            intent=IntentResult("UNCLEAR", 0.3),
            entities=ExtractedEntities(skills=["teaching"]),
            raw_text="I can teach"
        )
        
        # Enhance with context
        enhanced = tracker.enhance_intent_recognition(unclear_result)
        assert enhanced.intent.intent == "OFFER_HELP"  # Inferred from context
        
    def test_confirmation_detection(self):
        """Test detecting confirmations from context"""
        tracker = ContextTracker()
        
        # Set up confirmation context
        nlp_result = NLPResult(
            intent=IntentResult("OFFER_HELP", 0.9),
            entities=ExtractedEntities(),
            raw_text="I want to help"
        )
        tracker.add_turn("I want to help", nlp_result, "Is that correct?")
        
        # Test confirmation detection
        yes_result = NLPResult(
            intent=IntentResult("UNCLEAR", 0.2),
            entities=ExtractedEntities(),
            raw_text="Yes"
        )
        
        enhanced = tracker.enhance_intent_recognition(yes_result)
        assert enhanced.intent.intent == "CONFIRM"
        
    def test_denial_detection(self):
        """Test detecting denials from context"""
        tracker = ContextTracker()
        
        # Set up context with a question
        nlp_result = NLPResult(
            intent=IntentResult("OFFER_HELP", 0.9),
            entities=ExtractedEntities(),
            raw_text="I want to help"
        )
        tracker.add_turn("I want to help", nlp_result, "Are you sure?")
        
        # Test denial detection
        no_result = NLPResult(
            intent=IntentResult("UNCLEAR", 0.2),
            entities=ExtractedEntities(),
            raw_text="No"
        )
        
        enhanced = tracker.enhance_intent_recognition(no_result)
        assert enhanced.intent.intent == "DENY"
        
    def test_maintain_intent_with_entities(self):
        """Test maintaining intent when user provides entities"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Establish intent
        tracker.add_turn(
            "I want to help",
            processor.process("I want to help"),
            "When are you available?"
        )
        
        # Provide time (might be unclear intent)
        time_result = NLPResult(
            intent=IntentResult("UNCLEAR", 0.3),
            entities=ExtractedEntities(times=[{"day": "monday", "period": "evening"}]),
            raw_text="Monday evenings"
        )
        
        enhanced = tracker.enhance_intent_recognition(time_result)
        assert enhanced.intent.intent == "OFFER_HELP"  # Maintained from context


class TestClarificationSuggestions:
    """Test suggesting clarifications based on context"""
    
    def test_suggest_missing_info(self):
        """Test suggesting what information is missing"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Establish intent without all info
        tracker.add_turn(
            "I want to volunteer",
            processor.process("I want to volunteer"),
            "Great!"
        )
        
        should_ask, question = tracker.should_ask_clarification()
        assert should_ask == True
        assert "skills" in question
        assert "availability" in question
        assert "location" in question
        
    def test_no_clarification_when_complete(self):
        """Test no clarification needed when info is complete"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Add complete information
        tracker.add_turn(
            "I want to help with teaching on weekends at the library",
            processor.process("I want to help with teaching on weekends at the library"),
            "Perfect!"
        )
        
        should_ask, question = tracker.should_ask_clarification()
        assert should_ask == False
        assert question is None


class TestContextManagement:
    """Test context management functions"""
    
    def test_context_reset(self):
        """Test resetting context"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Add some context
        tracker.add_turn("I want to help", processor.process("I want to help"), "Great!")
        assert len(tracker.context.turns) > 0
        
        # Reset
        tracker.reset()
        assert len(tracker.context.turns) == 0
        assert tracker.context.established_intent is None
        
    def test_context_summary(self):
        """Test getting context summary"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Build up context
        tracker.add_turn(
            "I want to help with gardening",
            processor.process("I want to help with gardening"), 
            "Great!"
        )
        
        tracker.add_turn(
            "I'm free on weekends",
            processor.process("I'm free on weekends"),
            "Perfect!"
        )
        
        summary = tracker.get_context_summary()
        assert summary["num_turns"] == 2
        assert summary["established_intent"] == "SHARE_AVAILABILITY"
        assert "gardening" in summary["mentioned_entities"]["skills"]
        
    def test_max_history_limit(self):
        """Test that conversation history has a maximum limit"""
        tracker = ContextTracker()
        processor = NLPProcessor()
        
        # Add more than maxlen turns
        for i in range(15):
            tracker.add_turn(f"Turn {i}", processor.process("I want to help"), "OK")
            
        # Should only keep last 10
        assert len(tracker.context.turns) == 10
        assert tracker.context.get_last_user_input() == "Turn 14"


# Run with: pytest -xvs test_context_tracker.py