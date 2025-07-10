"""
Dialog Manager Tests

Test conversation flow management and response generation.
"""

import pytest
from ..dialog_manager import DialogManager, ConversationState, ConversationContext


class TestBasicDialogFlow:
    """Test basic conversation flows"""
    
    def test_volunteer_offer_flow(self):
        """Test a complete volunteer offer conversation"""
        dm = DialogManager()
        
        # Initial offer
        response = dm.process_turn("I want to help my community")
        assert "volunteer" in response.lower()
        assert dm.context.current_state == ConversationState.GATHERING_INFO
        
        # Provide skills
        response = dm.process_turn("I'm good at teaching and have experience with gardening")
        assert sorted(dm.context.gathered_info["skills"]) == ["gardening", "teaching"]
        
        # Provide availability
        response = dm.process_turn("I'm free on Saturday mornings")
        assert len(dm.context.gathered_info["times"]) == 1
        assert dm.context.gathered_info["times"][0]["day"] == "saturday"
        
        # Provide location
        response = dm.process_turn("I prefer to help at the community center")
        assert "community_center" in dm.context.gathered_info["locations"]
        
        # Should move to confirmation
        assert dm.context.current_state == ConversationState.CONFIRMING
        assert "confirm" in response.lower()
        
        # Confirm
        response = dm.process_turn("Yes, that's correct")
        assert dm.context.current_state == ConversationState.COMPLETE
        assert dm.context.gathered_info["confirmed"] == True
    
    def test_help_request_flow(self):
        """Test a help request conversation"""
        dm = DialogManager()
        
        # Initial request
        response = dm.process_turn("We need volunteers for our food bank")
        assert "assistance" in response or "help" in response
        assert dm.context.gathered_info["intent"] == "REQUEST_HELP"
    
    def test_unclear_intent_handling(self):
        """Test handling of unclear user input"""
        dm = DialogManager()
        
        response = dm.process_turn("Hello")
        assert "volunteer" in response or "help" in response
        assert dm.context.current_state == ConversationState.GATHERING_INFO
    
    def test_skill_sharing_flow(self):
        """Test skill sharing conversation"""
        dm = DialogManager()
        
        response = dm.process_turn("I'm a professional chef")
        assert "cooking" in dm.context.gathered_info["skills"]
        assert "available" in response.lower()
    
    def test_availability_sharing_flow(self):
        """Test availability sharing conversation"""
        dm = DialogManager()
        
        response = dm.process_turn("I'm free on weekends")
        assert dm.context.gathered_info["intent"] == "SHARE_AVAILABILITY"
        assert "activities" in response.lower() or "help" in response.lower()


class TestInformationGathering:
    """Test information gathering logic"""
    
    def test_missing_info_detection(self):
        """Test detection of missing information"""
        dm = DialogManager()
        
        # Offer help without details
        dm.process_turn("I want to volunteer")
        
        # Should ask for missing info
        missing_info = dm._get_missing_info()
        assert missing_info != ""
        assert any(word in missing_info.lower() for word in ["skills", "interests", "when", "where"])
    
    def test_incremental_info_gathering(self):
        """Test gathering information piece by piece"""
        dm = DialogManager()
        
        # Start with intent
        response1 = dm.process_turn("I want to help")
        assert dm.context.gathered_info["intent"] == "OFFER_HELP"
        
        # Add skills
        response2 = dm.process_turn("I can teach math")
        assert "math" in dm.context.gathered_info["skills"]
        assert "teaching" in dm.context.gathered_info["skills"]
        
        # Add time
        response3 = dm.process_turn("I'm available Tuesday evenings")
        assert len(dm.context.gathered_info["times"]) == 1
        
        # Add location
        response4 = dm.process_turn("I can help at the library")
        assert "library" in dm.context.gathered_info["locations"]
    
    def test_multiple_entities_in_one_turn(self):
        """Test extracting multiple entities from a single turn"""
        dm = DialogManager()
        
        response = dm.process_turn(
            "I'm a teacher available on weekends at the community center"
        )
        
        # Should extract all entities
        assert "teaching" in dm.context.gathered_info["skills"]
        assert any(t["day"] == "weekend" for t in dm.context.gathered_info["times"])
        assert "community_center" in dm.context.gathered_info["locations"]


class TestConfirmationFlow:
    """Test confirmation handling"""
    
    def test_positive_confirmation(self):
        """Test positive confirmation"""
        dm = DialogManager()
        
        # Go through proper flow to reach confirmation state
        dm.process_turn("I want to help")
        dm.process_turn("I can teach")
        dm.process_turn("Monday evenings")
        dm.process_turn("At the library")
        
        # Should be in confirming state now
        assert dm.context.current_state == ConversationState.CONFIRMING
        
        response = dm.process_turn("Yes, that's right")
        assert dm.context.gathered_info["confirmed"] == True
        assert dm.context.current_state == ConversationState.COMPLETE
    
    def test_negative_confirmation(self):
        """Test negative confirmation"""
        dm = DialogManager()
        
        # Go through proper flow
        dm.process_turn("I want to help")
        dm.process_turn("I can teach")
        dm.process_turn("Monday evenings")
        dm.process_turn("At the library")
        
        assert dm.context.current_state == ConversationState.CONFIRMING
        
        response = dm.process_turn("No, that's not right")
        assert dm.context.current_state == ConversationState.GATHERING_INFO
        assert "correct" in response.lower() or "start over" in response.lower()
    
    def test_unclear_confirmation(self):
        """Test unclear confirmation response"""
        dm = DialogManager()
        
        # Go through proper flow
        dm.process_turn("I want to help")
        dm.process_turn("I can teach")
        dm.process_turn("Monday evenings")
        dm.process_turn("At the library")
        
        assert dm.context.current_state == ConversationState.CONFIRMING
        
        response = dm.process_turn("Maybe")
        assert dm.context.current_state == ConversationState.CONFIRMING
        assert "yes or no" in response.lower()


class TestConversationManagement:
    """Test conversation state management"""
    
    def test_conversation_reset(self):
        """Test resetting conversation"""
        dm = DialogManager()
        
        # Have a conversation
        dm.process_turn("I want to help")
        dm.process_turn("I can teach")
        
        # Reset
        dm.reset_conversation()
        
        assert dm.context.current_state == ConversationState.GREETING
        assert len(dm.context.turns) == 0
        assert dm.context.gathered_info["intent"] is None
    
    def test_conversation_summary(self):
        """Test getting conversation summary"""
        dm = DialogManager()
        
        dm.process_turn("I want to volunteer")
        dm.process_turn("I'm good at gardening")
        
        summary = dm.get_conversation_summary()
        
        assert summary["turns"] == 2
        assert summary["state"] == ConversationState.GATHERING_INFO.value
        assert "gardening" in summary["gathered_info"]["skills"]
        assert summary["confirmed"] == False
    
    def test_turn_history(self):
        """Test conversation turn tracking"""
        dm = DialogManager()
        
        inputs = [
            "I want to help",
            "I can teach math",
            "Saturday mornings work for me"
        ]
        
        for user_input in inputs:
            dm.process_turn(user_input)
        
        assert len(dm.context.turns) == 3
        
        # Check turn details
        first_turn = dm.context.turns[0]
        assert first_turn.user_input == "I want to help"
        assert first_turn.nlp_result.intent.intent == "OFFER_HELP"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_input(self):
        """Test handling empty input"""
        dm = DialogManager()
        
        response = dm.process_turn("")
        assert response  # Should return something
        assert dm.context.current_state == ConversationState.GATHERING_INFO
    
    def test_very_long_input(self):
        """Test handling very long input"""
        dm = DialogManager()
        
        long_input = "I want to help " * 50
        response = dm.process_turn(long_input)
        
        assert response  # Should handle gracefully
        assert dm.context.gathered_info["intent"] == "OFFER_HELP"
    
    def test_repeated_information(self):
        """Test handling repeated information"""
        dm = DialogManager()
        
        dm.process_turn("I can teach")
        dm.process_turn("I'm good at teaching")
        
        # Should not duplicate
        assert dm.context.gathered_info["skills"].count("teaching") == 1


# Run with: pytest -xvs test_dialog_manager.py