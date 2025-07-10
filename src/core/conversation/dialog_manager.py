"""
Dialog Manager for CivicForge

Manages conversation flow, generates appropriate responses,
and guides users through civic engagement interactions.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

from ..nlp.nlp_processor import NLPProcessor, NLPResult


class ConversationState(Enum):
    """Possible states in a conversation"""
    GREETING = "greeting"
    GATHERING_INFO = "gathering_info"
    CONFIRMING = "confirming"
    MATCHING = "matching"
    COMPLETE = "complete"


@dataclass
class DialogTurn:
    """A single turn in the dialog"""
    user_input: str
    system_response: str
    nlp_result: Optional[NLPResult] = None
    state: ConversationState = ConversationState.GREETING


# Import the unified ConversationContext from context_tracker
from .context_tracker import ContextTracker, ConversationTurn as CTTurn

# Import interfaces for future features
from ..interfaces import (
    LocalController, MockLocalController,
    ApprovalRequest, ActionType,
    PrivacyManager, MockPrivacyManager
)


class DialogManager:
    """Manages conversation flow and response generation"""
    
    def __init__(self, 
                 context_tracker: ContextTracker = None,
                 local_controller: LocalController = None,
                 privacy_manager: PrivacyManager = None):
        self.context_tracker = context_tracker or ContextTracker()
        self.local_controller = local_controller or MockLocalController()
        self.privacy_manager = privacy_manager or MockPrivacyManager()
        
        # Initialize NLP processor with privacy/consent managers
        self.nlp_processor = NLPProcessor(privacy_manager=self.privacy_manager)
        
        self.current_state = ConversationState.GREETING
        self.gathered_info = {
            "intent": None,
            "skills": [],
            "times": [],
            "locations": [],
            "confirmed": False
        }
        
        # State handler mapping
        self.state_handlers = {
            ConversationState.GREETING: self._handle_initial_intent,
            ConversationState.GATHERING_INFO: self._handle_info_gathering,
            ConversationState.CONFIRMING: self._handle_confirmation,
            ConversationState.MATCHING: self._handle_matching,
            ConversationState.COMPLETE: self._handle_complete
        }
        
    def process_turn(self, user_input: str) -> str:
        """Process a user turn and generate response"""
        # Process input through NLP
        nlp_result = self.nlp_processor.process(user_input)
        
        # Update context with gathered information
        self._update_gathered_info(nlp_result)
        
        # Determine next state and response
        next_state, response = self._determine_response(nlp_result)
        
        # Create and store dialog turn
        turn = DialogTurn(
            user_input=user_input,
            system_response=response,
            nlp_result=nlp_result,
            state=next_state
        )
        self.current_state = next_state
        
        # Also update context tracker
        self.context_tracker.add_turn(user_input, nlp_result, response)
        
        return response
    
    def _determine_response(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Determine the appropriate response based on current state and NLP results"""
        
        # Special handling for unclear intent
        if nlp_result.needs_clarification() and self.current_state != ConversationState.CONFIRMING:
            # Check if we still got useful entities
            if (self.current_state == ConversationState.GATHERING_INFO and 
                (nlp_result.entities.skills or nlp_result.entities.times or nlp_result.entities.locations)):
                # Continue with current handler since we have useful data
                pass
            else:
                # Return clarification request
                return (
                    ConversationState.GATHERING_INFO,
                    nlp_result.intent.suggested_clarification or 
                    "I'm not sure I understood. Are you looking to volunteer or do you need help?"
                )
        
        # Use state handler pattern
        handler = self.state_handlers.get(self.current_state, self._handle_default)
        return handler(nlp_result)
    
    def _handle_initial_intent(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Handle the initial intent from the user"""
        intent = nlp_result.intent.intent
        
        if intent == "OFFER_HELP":
            missing_info = self._get_missing_info()
            if missing_info:
                return (
                    ConversationState.GATHERING_INFO,
                    f"Great! I'd love to help you volunteer. {missing_info}"
                )
            else:
                return self._create_confirmation()
                
        elif intent == "REQUEST_HELP":
            return (
                ConversationState.GATHERING_INFO,
                "I understand you need assistance. Can you tell me more about what kind of help you're looking for?"
            )
            
        elif intent == "SHARE_SKILLS":
            skills = ", ".join(nlp_result.entities.skills) if nlp_result.entities.skills else "your skills"
            return (
                ConversationState.GATHERING_INFO,
                f"Wonderful! You have experience with {skills}. When are you available to help?"
            )
            
        elif intent == "SHARE_AVAILABILITY":
            return (
                ConversationState.GATHERING_INFO,
                "Thank you for sharing your availability. What kinds of activities would you like to help with?"
            )
            
        return (
            ConversationState.GATHERING_INFO,
            "Thank you for reaching out. Could you tell me a bit more about how you'd like to get involved?"
        )
    
    def _handle_info_gathering(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Continue gathering missing information"""
        missing_info = self._get_missing_info()
        
        if missing_info:
            return (
                ConversationState.GATHERING_INFO,
                f"Thank you! {missing_info}"
            )
        else:
            return self._create_confirmation()
    
    def _handle_confirmation(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Handle user confirmation of gathered information"""
        # Only handle confirmation if we're actually in confirming state
        if self.current_state != ConversationState.CONFIRMING:
            # Not in confirmation state, treat as regular input
            return self._handle_info_gathering(nlp_result)
        
        # Simple confirmation detection
        user_input_lower = nlp_result.raw_text.lower()
        # Check negative first since "not right" contains "right"
        if any(word in user_input_lower for word in ["no", "wrong", "incorrect", "not right"]):
            return (
                ConversationState.GATHERING_INFO,
                "I apologize for the confusion. Let's start over. What would you like to correct?"
            )
        elif any(word in user_input_lower for word in ["yes", "correct", "right", "sure"]):
            self.gathered_info["confirmed"] = True
            
            # Request approval to share data for matching
            approval_request = ApprovalRequest(
                action_type=ActionType.SHARE_PROFILE,
                description="Share your interests and availability to find matching opportunities",
                data_to_share={
                    "skills": self.gathered_info["skills"],
                    "times": self.gathered_info["times"],
                    "locations": self.gathered_info["locations"]
                },
                purpose="opportunity_matching"
            )
            
            approval = self.local_controller.request_approval(approval_request)
            
            if approval.approved:
                return (
                    ConversationState.COMPLETE,
                    "Perfect! I'll help you find matching opportunities. Let me search for activities that match your preferences..."
                )
            else:
                return (
                    ConversationState.GATHERING_INFO,
                    "I understand you'd prefer not to share that information. Is there anything else I can help you with?"
                )
        else:
            return (
                ConversationState.CONFIRMING,
                "I'm not sure if that's a yes or no. Do the details I summarized look correct?"
            )
    
    def _get_missing_info(self) -> str:
        """Determine what information is still needed"""
        info = self.gathered_info
        missing_prompts = []
        
        # Check what's missing based on intent
        if info["intent"] in ["OFFER_HELP", "SHARE_SKILLS", "SHARE_AVAILABILITY"]:
            if not info["skills"]:
                missing_prompts.append("What skills or interests do you have?")
            if not info["times"]:
                missing_prompts.append("When are you available?")
            if not info["locations"]:
                missing_prompts.append("Where would you prefer to volunteer?")
                
        elif info["intent"] == "REQUEST_HELP":
            if not info["skills"]:
                missing_prompts.append("What kind of help do you need?")
            if not info["times"]:
                missing_prompts.append("When do you need assistance?")
            if not info["locations"]:
                missing_prompts.append("Where is the help needed?")
        
        return " ".join(missing_prompts[:1])  # Ask one question at a time
    
    def _create_confirmation(self) -> Tuple[ConversationState, str]:
        """Create a confirmation message with all gathered information"""
        info = self.gathered_info
        
        parts = ["Let me confirm what I've understood:"]
        
        if info["intent"] == "OFFER_HELP":
            parts.append("You want to volunteer")
        elif info["intent"] == "REQUEST_HELP":
            parts.append("You need help")
            
        if info["skills"]:
            parts.append(f"Skills/Interests: {', '.join(info['skills'])}")
            
        if info["times"]:
            time_strs = []
            for time in info["times"]:
                if time["day"] == "any":
                    time_strs.append(f"{time['period']}s")
                else:
                    time_strs.append(f"{time['day']} {time['period']}")
            parts.append(f"Available: {', '.join(time_strs)}")
            
        if info["locations"]:
            parts.append(f"Preferred locations: {', '.join(info['locations'])}")
            
        parts.append("\nIs this correct?")
        
        return (
            ConversationState.CONFIRMING,
            "\n".join(parts)
        )
    
    def reset_conversation(self):
        """Reset the conversation to start fresh"""
        self.context_tracker.reset()
        self.nlp_processor.reset_context()
        self.current_state = ConversationState.GREETING
        self.gathered_info = {
            "intent": None,
            "skills": [],
            "times": [],
            "locations": [],
            "confirmed": False
        }
    
    def get_conversation_summary(self) -> Dict:
        """Get a summary of the conversation so far"""
        tracker_summary = self.context_tracker.get_context_summary()
        return {
            "state": self.current_state.value,
            "turns": tracker_summary["num_turns"],
            "gathered_info": self.gathered_info,
            "confirmed": self.gathered_info.get("confirmed", False),
            "tracker_summary": tracker_summary
        }
    
    def _update_gathered_info(self, nlp_result: NLPResult):
        """Update gathered information from NLP results"""
        if nlp_result.intent.intent != "UNCLEAR":
            self.gathered_info["intent"] = nlp_result.intent.intent
        
        # Accumulate entities
        for skill in nlp_result.entities.skills:
            if skill not in self.gathered_info["skills"]:
                self.gathered_info["skills"].append(skill)
        
        for time in nlp_result.entities.times:
            if time not in self.gathered_info["times"]:
                self.gathered_info["times"].append(time)
                
        for location in nlp_result.entities.locations:
            if location not in self.gathered_info["locations"]:
                self.gathered_info["locations"].append(location)
    
    def _handle_default(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Default handler for unexpected states"""
        return (
            ConversationState.GATHERING_INFO,
            "Thank you for that information. Can you tell me more?"
        )
    
    def _handle_matching(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Handle matching state (currently just transitions to complete)"""
        return (
            ConversationState.COMPLETE,
            "I'm searching for opportunities that match your preferences..."
        )
    
    def _handle_complete(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Handle complete state"""
        return (
            ConversationState.COMPLETE,
            "Your request has been processed. Is there anything else I can help you with?"
        )
