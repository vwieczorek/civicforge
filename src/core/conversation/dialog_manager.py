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


@dataclass
class ConversationContext:
    """Maintains conversation state and history"""
    current_state: ConversationState = ConversationState.GREETING
    turns: List[DialogTurn] = None
    gathered_info: Dict = None
    
    def __post_init__(self):
        if self.turns is None:
            self.turns = []
        if self.gathered_info is None:
            self.gathered_info = {
                "intent": None,
                "skills": [],
                "times": [],
                "locations": [],
                "confirmed": False
            }
    
    def add_turn(self, turn: DialogTurn):
        """Add a turn to the conversation history"""
        self.turns.append(turn)
        self.current_state = turn.state
    
    def update_gathered_info(self, nlp_result: NLPResult):
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


class DialogManager:
    """Manages conversation flow and response generation"""
    
    def __init__(self):
        self.nlp_processor = NLPProcessor()
        self.context = ConversationContext()
        
    def process_turn(self, user_input: str) -> str:
        """Process a user turn and generate response"""
        # Process input through NLP
        nlp_result = self.nlp_processor.process(user_input)
        
        # Update context with gathered information
        self.context.update_gathered_info(nlp_result)
        
        # Determine next state and response
        next_state, response = self._determine_response(nlp_result)
        
        # Create and store dialog turn
        turn = DialogTurn(
            user_input=user_input,
            system_response=response,
            nlp_result=nlp_result,
            state=next_state
        )
        self.context.add_turn(turn)
        
        return response
    
    def _determine_response(self, nlp_result: NLPResult) -> Tuple[ConversationState, str]:
        """Determine the appropriate response based on current state and NLP results"""
        
        # Check state-specific handlers first
        # Confirming state needs priority to handle "yes/no" responses
        if self.context.current_state == ConversationState.CONFIRMING:
            return self._handle_confirmation(nlp_result)
        
        # If we're already gathering info and get entities, that's still useful
        if (self.context.current_state == ConversationState.GATHERING_INFO and 
            nlp_result.needs_clarification() and
            (nlp_result.entities.skills or nlp_result.entities.times or nlp_result.entities.locations)):
            # We got useful entities even if intent is unclear
            return self._handle_info_gathering(nlp_result)
        
        # Handle unclear intent
        if nlp_result.needs_clarification():
            return (
                ConversationState.GATHERING_INFO,
                nlp_result.intent.suggested_clarification or 
                "I'm not sure I understood. Are you looking to volunteer or do you need help?"
            )
        
        # Initial greeting/intent establishment
        if self.context.current_state == ConversationState.GREETING:
            return self._handle_initial_intent(nlp_result)
        
        # Gathering additional information
        elif self.context.current_state == ConversationState.GATHERING_INFO:
            return self._handle_info_gathering(nlp_result)
        
        # Default response
        return (
            ConversationState.GATHERING_INFO,
            "Thank you for that information. Can you tell me more?"
        )
    
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
        if self.context.current_state != ConversationState.CONFIRMING:
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
            self.context.gathered_info["confirmed"] = True
            return (
                ConversationState.COMPLETE,
                "Perfect! I'll help you find matching opportunities. Let me search for activities that match your preferences..."
            )
        else:
            return (
                ConversationState.CONFIRMING,
                "I'm not sure if that's a yes or no. Do the details I summarized look correct?"
            )
    
    def _get_missing_info(self) -> str:
        """Determine what information is still needed"""
        info = self.context.gathered_info
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
        info = self.context.gathered_info
        
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
        self.context = ConversationContext()
        self.nlp_processor.reset_context()
    
    def get_conversation_summary(self) -> Dict:
        """Get a summary of the conversation so far"""
        return {
            "state": self.context.current_state.value,
            "turns": len(self.context.turns),
            "gathered_info": self.context.gathered_info,
            "confirmed": self.context.gathered_info.get("confirmed", False)
        }