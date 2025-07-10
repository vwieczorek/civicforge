"""
NLP Processor Integration Tests

Test the combined intent recognition and entity extraction pipeline.
"""

import pytest
from ..nlp_processor import NLPProcessor, NLPResult


class TestNLPIntegration:
    """Test integrated NLP processing"""
    
    def test_complete_volunteer_offer(self):
        """Process a complete volunteer offer with all entity types"""
        processor = NLPProcessor()
        
        text = "I want to help with teaching math on Saturday mornings at the community center"
        result = processor.process(text)
        
        # Check intent
        assert result.intent.intent == "OFFER_HELP"
        assert result.intent.confidence > 0.7
        
        # Check entities
        assert "teaching" in result.entities.skills
        assert "math" in result.entities.skills
        assert {"day": "saturday", "period": "morning"} in result.entities.times
        assert "community_center" in result.entities.locations
        
        # Check summary
        summary = result.get_summary()
        assert "User wants to help" in summary
        assert "teaching" in summary
        assert "saturday morning" in summary
    
    def test_help_request_processing(self):
        """Process a help request"""
        processor = NLPProcessor()
        
        text = "We need volunteers with gardening skills at the local park this weekend"
        result = processor.process(text)
        
        assert result.intent.intent == "REQUEST_HELP"
        assert "gardening" in result.entities.skills
        assert "park" in result.entities.locations
        assert {"day": "weekend", "period": "all_day"} in result.entities.times
    
    def test_availability_sharing(self):
        """Process availability sharing"""
        processor = NLPProcessor()
        
        text = "I'm free Tuesday evenings and can help with computer support"
        result = processor.process(text)
        
        assert result.intent.intent == "SHARE_AVAILABILITY"
        assert {"day": "tuesday", "period": "evening"} in result.entities.times
        assert "computer" in result.entities.skills
    
    def test_skill_sharing(self):
        """Process skill sharing"""
        processor = NLPProcessor()
        
        text = "I'm a professional chef and also good at mentoring young people"
        result = processor.process(text)
        
        assert result.intent.intent == "SHARE_SKILLS"
        assert "cooking" in result.entities.skills
        assert "mentoring" in result.entities.skills
    
    def test_unclear_intent_handling(self):
        """Handle unclear intentions gracefully"""
        processor = NLPProcessor()
        
        text = "Hello there"
        result = processor.process(text)
        
        assert result.intent.intent == "UNCLEAR"
        assert result.needs_clarification()
        assert result.intent.suggested_clarification is not None
    
    def test_summary_generation(self):
        """Test human-readable summary generation"""
        processor = NLPProcessor()
        
        test_cases = [
            (
                "I can teach reading on weekends at the library",
                ["User is sharing skills", "Skills: reading, teaching", "Available: weekend", "Locations: library"]
            ),
            (
                "Looking for help with meal preparation",
                ["User needs assistance", "Skills: cooking"]
            ),
            (
                "I have mornings free",
                ["User is sharing availability", "Available: mornings"]
            ),
        ]
        
        for text, expected_parts in test_cases:
            result = processor.process(text)
            summary = result.get_summary()
            for part in expected_parts:
                assert part in summary, f"Expected '{part}' in summary: {summary}"
    
    def test_context_reset(self):
        """Test context reset functionality"""
        processor = NLPProcessor()
        
        # Process something
        processor.process("I want to help")
        
        # Reset context
        processor.reset_context()
        
        # Verify context was reset (would be more meaningful with actual context tracking)
        assert processor.intent_recognizer.context == {}


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_input(self):
        """Handle empty input gracefully"""
        processor = NLPProcessor()
        
        result = processor.process("")
        assert result.intent.intent == "UNCLEAR"
        assert result.entities.skills == []
        assert result.entities.times == []
        assert result.entities.locations == []
    
    def test_very_long_input(self):
        """Handle very long input"""
        processor = NLPProcessor()
        
        long_text = "I want to help " * 100
        result = processor.process(long_text)
        
        assert result.intent.intent == "OFFER_HELP"
        # Should still process correctly
    
    def test_mixed_case_input(self):
        """Handle mixed case input"""
        processor = NLPProcessor()
        
        text = "I WANT TO HELP with TEACHING at the Community Center"
        result = processor.process(text)
        
        assert result.intent.intent == "OFFER_HELP"
        assert "teaching" in result.entities.skills
        assert "community_center" in result.entities.locations


# Run with: pytest -xvs test_nlp_processor.py