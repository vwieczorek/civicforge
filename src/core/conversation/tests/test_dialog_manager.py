"""
Tests for Dialog Manager
"""

import pytest
from ..dialog_manager import (
    DialogManager,
    ConversationState,
    DialogTurn
)
from ..context_tracker import ContextTracker
from ...interfaces import MockLocalController, MockPrivacyManager


@pytest.fixture
def dialog_manager():
    """Create a DialogManager instance with mocked dependencies"""
    return DialogManager(
        context_tracker=ContextTracker(),
        local_controller=MockLocalController(),
        privacy_manager=MockPrivacyManager()
    )


def test_initial_state(dialog_manager):
    """Test dialog manager starts in correct state"""
    assert dialog_manager.current_state == ConversationState.GREETING
    assert dialog_manager.gathered_info["intent"] is None
    assert dialog_manager.gathered_info["skills"] == []


def test_process_offer_help(dialog_manager):
    """Test processing an offer to help"""
    response = dialog_manager.process_turn("I want to help in my community")
    
    assert "volunteer" in response.lower() or "help" in response.lower()
    assert dialog_manager.current_state == ConversationState.GATHERING_INFO
    assert dialog_manager.gathered_info["intent"] == "OFFER_HELP"


def test_process_request_help(dialog_manager):
    """Test processing a request for help"""
    response = dialog_manager.process_turn("I need help with my garden")
    
    assert "assistance" in response.lower() or "help" in response.lower()
    assert dialog_manager.current_state == ConversationState.GATHERING_INFO
    assert dialog_manager.gathered_info["intent"] == "REQUEST_HELP"


def test_gather_skills_information(dialog_manager):
    """Test gathering skills information"""
    dialog_manager.process_turn("I want to volunteer")
    response = dialog_manager.process_turn("I'm good at teaching and programming")
    
    assert dialog_manager.gathered_info["skills"] == ["teaching", "programming"]
    # Should ask for more info (time or location)
    assert "when" in response.lower() or "where" in response.lower()


def test_gather_time_information(dialog_manager):
    """Test gathering availability information"""
    dialog_manager.process_turn("I want to help")
    dialog_manager.process_turn("I can teach")
    response = dialog_manager.process_turn("I'm available on Saturday mornings")
    
    assert len(dialog_manager.gathered_info["times"]) > 0
    assert dialog_manager.gathered_info["times"][0]["day"] == "saturday"
    assert dialog_manager.gathered_info["times"][0]["period"] == "morning"


def test_gather_location_information(dialog_manager):
    """Test gathering location information"""
    dialog_manager.process_turn("I want to volunteer")
    dialog_manager.process_turn("I can do gardening")
    dialog_manager.process_turn("Weekends work for me")
    response = dialog_manager.process_turn("I prefer working downtown or at the library")
    
    assert "downtown" in dialog_manager.gathered_info["locations"]
    assert "library" in dialog_manager.gathered_info["locations"]


def test_confirmation_flow(dialog_manager):
    """Test the confirmation flow"""
    # Provide all required information
    dialog_manager.process_turn("I want to help")
    dialog_manager.process_turn("I can teach programming")
    dialog_manager.process_turn("Saturday mornings work for me")
    response = dialog_manager.process_turn("I can work at the downtown library")
    
    # Should move to confirmation state
    assert dialog_manager.current_state == ConversationState.CONFIRMING
    assert "confirm" in response.lower()
    assert "teaching" in response or "programming" in response


def test_confirmation_yes(dialog_manager):
    """Test confirming the gathered information"""
    # Setup complete information
    dialog_manager.current_state = ConversationState.CONFIRMING
    dialog_manager.gathered_info = {
        "intent": "OFFER_HELP",
        "skills": ["teaching"],
        "times": [{"day": "saturday", "period": "morning"}],
        "locations": ["library"],
        "confirmed": False
    }
    
    response = dialog_manager.process_turn("Yes, that's correct")
    
    assert dialog_manager.gathered_info["confirmed"] is True
    assert dialog_manager.current_state == ConversationState.COMPLETE
    assert "opportunities" in response.lower() or "matching" in response.lower()


def test_confirmation_no(dialog_manager):
    """Test rejecting the confirmation"""
    dialog_manager.current_state = ConversationState.CONFIRMING
    dialog_manager.gathered_info["intent"] = "OFFER_HELP"
    
    response = dialog_manager.process_turn("No, that's not right")
    
    assert dialog_manager.current_state == ConversationState.GATHERING_INFO
    assert "correct" in response.lower() or "start over" in response.lower()


def test_unclear_intent_handling(dialog_manager):
    """Test handling unclear intent"""
    response = dialog_manager.process_turn("Hello there")
    
    # Should ask for clarification
    assert "volunteer" in response.lower() or "help" in response.lower()
    assert dialog_manager.current_state == ConversationState.GATHERING_INFO


def test_reset_conversation(dialog_manager):
    """Test resetting the conversation"""
    # Add some data
    dialog_manager.process_turn("I want to help")
    dialog_manager.process_turn("I can teach")
    
    # Reset
    dialog_manager.reset_conversation()
    
    assert dialog_manager.current_state == ConversationState.GREETING
    assert dialog_manager.gathered_info["intent"] is None
    assert dialog_manager.gathered_info["skills"] == []


def test_get_conversation_summary(dialog_manager):
    """Test getting conversation summary"""
    dialog_manager.process_turn("I want to volunteer")
    dialog_manager.process_turn("I know programming")
    
    summary = dialog_manager.get_conversation_summary()
    
    assert summary["state"] == ConversationState.GATHERING_INFO.value
    assert summary["turns"] == 2
    assert summary["gathered_info"]["intent"] == "OFFER_HELP"
    assert "programming" in summary["gathered_info"]["skills"]


def test_privacy_budget_exhaustion(dialog_manager):
    """Test handling when privacy budget is exhausted"""
    # Exhaust the privacy budget
    dialog_manager.privacy_manager._budgets["anonymous"] = dialog_manager.privacy_manager.check_privacy_budget("anonymous")
    dialog_manager.privacy_manager._budgets["anonymous"].queries_used = 100
    
    response = dialog_manager.process_turn("I want to help")
    
    assert "privacy limit" in response.lower()


def test_approval_flow(dialog_manager):
    """Test the approval flow when confirming"""
    # Setup for confirmation with auto-approvable action
    dialog_manager.current_state = ConversationState.CONFIRMING
    dialog_manager.gathered_info = {
        "intent": "OFFER_HELP",
        "skills": ["teaching"],
        "times": [{"day": "saturday", "period": "morning"}],
        "locations": ["library"],
        "confirmed": False
    }
    
    # The mock controller auto-approves SHARE_SKILLS and SHARE_AVAILABILITY
    response = dialog_manager.process_turn("Yes")
    
    # Check that approval was requested
    assert len(dialog_manager.local_controller._approval_log) > 0
    assert dialog_manager.current_state == ConversationState.COMPLETE


def test_accumulate_entities(dialog_manager):
    """Test that entities accumulate across turns"""
    dialog_manager.process_turn("I want to help")
    dialog_manager.process_turn("I can teach")
    dialog_manager.process_turn("I also know programming")
    
    skills = dialog_manager.gathered_info["skills"]
    assert "teaching" in skills
    assert "programming" in skills
    assert len(skills) == 2


def test_multiple_time_slots(dialog_manager):
    """Test handling multiple time slots"""
    dialog_manager.process_turn("I want to volunteer")
    dialog_manager.process_turn("I'm available Saturday mornings and Wednesday afternoons")
    
    times = dialog_manager.gathered_info["times"]
    assert len(times) == 2
    
    # Check both time slots were captured
    days = [t["day"] for t in times]
    assert "saturday" in days
    assert "wednesday" in days


def test_share_skills_intent(dialog_manager):
    """Test SHARE_SKILLS intent handling"""
    response = dialog_manager.process_turn("I have experience in gardening and cooking")
    
    assert dialog_manager.gathered_info["intent"] == "SHARE_SKILLS"
    assert "gardening" in dialog_manager.gathered_info["skills"]
    assert "cooking" in dialog_manager.gathered_info["skills"]
    assert "available" in response.lower()


def test_share_availability_intent(dialog_manager):
    """Test SHARE_AVAILABILITY intent handling"""
    response = dialog_manager.process_turn("I'm free on weekends")
    
    assert dialog_manager.gathered_info["intent"] == "SHARE_AVAILABILITY"
    assert "activities" in response.lower() or "help" in response.lower()


def test_edge_case_empty_gathered_info(dialog_manager):
    """Test edge case with no gathered information"""
    # Force a confirmation state with no info
    dialog_manager.current_state = ConversationState.GATHERING_INFO
    
    # Should ask for missing information
    missing_info = dialog_manager._get_missing_info()
    assert missing_info != ""


def test_confirmation_ambiguous_response(dialog_manager):
    """Test handling ambiguous confirmation response"""
    dialog_manager.current_state = ConversationState.CONFIRMING
    dialog_manager.gathered_info["intent"] = "OFFER_HELP"
    
    response = dialog_manager.process_turn("I'm not sure")
    
    assert dialog_manager.current_state == ConversationState.CONFIRMING
    assert "yes or no" in response.lower()