"""
Context Tracker for CivicForge

Tracks conversation context and history to improve intent recognition
and maintain conversational coherence.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import deque

from ..nlp.nlp_processor import NLPResult


@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    timestamp: datetime
    user_input: str
    nlp_result: NLPResult
    system_response: str
    
    
@dataclass 
class ConversationContext:
    """Maintains the context of an ongoing conversation"""
    turns: deque = field(default_factory=lambda: deque(maxlen=10))  # Keep last 10 turns
    current_topic: Optional[str] = None
    established_intent: Optional[str] = None
    mentioned_entities: Dict[str, List] = field(default_factory=dict)
    
    def add_turn(self, turn: ConversationTurn):
        """Add a new turn to the conversation history"""
        self.turns.append(turn)
        
        # Update established intent if we have a clear one
        if turn.nlp_result.intent.intent != "UNCLEAR":
            self.established_intent = turn.nlp_result.intent.intent
            
        # Accumulate mentioned entities
        if turn.nlp_result.entities.skills:
            if "skills" not in self.mentioned_entities:
                self.mentioned_entities["skills"] = []
            for skill in turn.nlp_result.entities.skills:
                if skill not in self.mentioned_entities["skills"]:
                    self.mentioned_entities["skills"].append(skill)
            
        if turn.nlp_result.entities.times:
            if "times" not in self.mentioned_entities:
                self.mentioned_entities["times"] = []
            for time in turn.nlp_result.entities.times:
                # Check if this time is already tracked
                if not any(t["day"] == time["day"] and t["period"] == time["period"] 
                          for t in self.mentioned_entities["times"]):
                    self.mentioned_entities["times"].append(time)
            
        if turn.nlp_result.entities.locations:
            if "locations" not in self.mentioned_entities:
                self.mentioned_entities["locations"] = []
            for location in turn.nlp_result.entities.locations:
                if location not in self.mentioned_entities["locations"]:
                    self.mentioned_entities["locations"].append(location)
    
    def get_recent_turns(self, n: int = 3) -> List[ConversationTurn]:
        """Get the n most recent turns"""
        return list(self.turns)[-n:]
    
    def get_last_user_input(self) -> Optional[str]:
        """Get the most recent user input"""
        if self.turns:
            return self.turns[-1].user_input
        return None
    
    def get_conversation_summary(self) -> Dict:
        """Get a summary of the conversation so far"""
        return {
            "num_turns": len(self.turns),
            "established_intent": self.established_intent,
            "mentioned_entities": self.mentioned_entities,
            "current_topic": self.current_topic
        }


class ContextTracker:
    """Tracks and analyzes conversation context"""
    
    def __init__(self):
        self.context = ConversationContext()
        self.intent_keywords = {
            "OFFER_HELP": ["yes", "sure", "okay", "definitely", "absolutely"],
            "REQUEST_HELP": ["yes", "please", "need", "urgent"],
            "CONFIRM": ["yes", "correct", "right", "exactly", "that's right"],
            "DENY": ["no", "incorrect", "wrong", "not right", "actually"],
        }
        
    def add_turn(self, user_input: str, nlp_result: NLPResult, system_response: str):
        """Add a conversation turn and update context"""
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_input=user_input,
            nlp_result=nlp_result,
            system_response=system_response
        )
        self.context.add_turn(turn)
        
    def enhance_intent_recognition(self, current_nlp_result: NLPResult) -> NLPResult:
        """Enhance intent recognition using conversation context"""
        # If the current intent is unclear, try to infer from context
        if current_nlp_result.intent.intent == "UNCLEAR":
            enhanced_intent = self._infer_intent_from_context(current_nlp_result.raw_text)
            if enhanced_intent:
                # Create a new result with enhanced intent
                current_nlp_result.intent.intent = enhanced_intent
                current_nlp_result.intent.confidence = 0.7  # Moderate confidence from context
                
        return current_nlp_result
    
    def _infer_intent_from_context(self, user_input: str) -> Optional[str]:
        """Try to infer intent from context when the direct intent is unclear"""
        user_input_lower = user_input.lower().strip()
        
        # Check if this might be a confirmation/denial
        if len(self.context.turns) > 0:
            last_response = self.context.turns[-1].system_response.lower()
            
            # If last response was a question
            if "?" in last_response:
                # Check for confirmation patterns
                for word in self.intent_keywords["CONFIRM"]:
                    if word in user_input_lower:
                        return "CONFIRM"
                        
                # Check for denial patterns  
                for word in self.intent_keywords["DENY"]:
                    if word in user_input_lower:
                        return "DENY"
                        
                # If it contains time/location/skill entities, maintain the established intent
                if self.context.established_intent and self._contains_relevant_entities(user_input_lower):
                    return self.context.established_intent
                    
        # Check if user is continuing a previous intent
        if self.context.established_intent:
            # If they're providing more details (entities), keep the same intent
            if self._contains_relevant_entities(user_input_lower):
                return self.context.established_intent
                
        return None
    
    def _contains_relevant_entities(self, text: str) -> bool:
        """Check if text contains entities relevant to civic engagement"""
        # Simple heuristic - could be enhanced
        entity_indicators = [
            # Time indicators
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "morning", "afternoon", "evening", "weekend", "weekday",
            # Location indicators
            "center", "library", "park", "school", "church", "downtown",
            # Skill indicators
            "teach", "garden", "cook", "drive", "code", "mentor"
        ]
        
        return any(indicator in text for indicator in entity_indicators)
    
    def get_context_summary(self) -> Dict:
        """Get the current context summary"""
        return self.context.get_conversation_summary()
    
    def reset(self):
        """Reset the context tracker"""
        self.context = ConversationContext()
        
    def should_ask_clarification(self) -> Tuple[bool, Optional[str]]:
        """Determine if we should ask for clarification based on context"""
        summary = self.get_context_summary()
        
        # If we have an established intent but missing key information
        if summary["established_intent"] in ["OFFER_HELP", "REQUEST_HELP"]:
            entities = summary["mentioned_entities"]
            
            # Check what's missing
            missing = []
            if not entities.get("skills"):
                missing.append("skills or interests")
            if not entities.get("times"):
                missing.append("availability")
            if not entities.get("locations"):  
                missing.append("preferred location")
                
            if missing:
                return True, f"Could you also share your {' and '.join(missing)}?"
                
        return False, None