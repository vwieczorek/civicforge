"""
NLP Processor for CivicForge

Combines intent recognition and entity extraction to provide
comprehensive natural language understanding.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict

from .intent_recognition import IntentRecognizer, IntentResult
from .entity_extraction import EntityExtractor, ExtractedEntities
from ..interfaces import PrivacyManager, ConsentManager, MockPrivacyManager, MockConsentManager
from ..interfaces import ConsentType


@dataclass
class NLPResult:
    """Combined result of NLP processing"""
    
    intent: IntentResult
    entities: ExtractedEntities
    raw_text: str
    
    def needs_clarification(self) -> bool:
        """Check if we need to ask the user for clarification"""
        return self.intent.intent == "UNCLEAR"
    
    def get_summary(self) -> str:
        """Get a human-readable summary of what was understood"""
        summary_parts = []
        
        # Intent summary
        if self.intent.intent == "OFFER_HELP":
            summary_parts.append("User wants to help")
        elif self.intent.intent == "REQUEST_HELP":
            summary_parts.append("User needs assistance")
        elif self.intent.intent == "SHARE_AVAILABILITY":
            summary_parts.append("User is sharing availability")
        elif self.intent.intent == "SHARE_SKILLS":
            summary_parts.append("User is sharing skills")
        
        # Add entity details
        if self.entities.skills:
            skills_str = ", ".join(self.entities.skills)
            summary_parts.append(f"Skills: {skills_str}")
            
        if self.entities.times:
            time_strs = []
            for time in self.entities.times:
                if time["day"] == "any":
                    time_strs.append(f"{time['period']}s")
                else:
                    time_strs.append(f"{time['day']} {time['period']}")
            summary_parts.append(f"Available: {', '.join(time_strs)}")
            
        if self.entities.locations:
            locations_str = ", ".join(self.entities.locations)
            summary_parts.append(f"Locations: {locations_str}")
            
        return " | ".join(summary_parts) if summary_parts else "No clear information extracted"


class NLPProcessor:
    """Main NLP processing pipeline"""
    
    def __init__(self, 
                 privacy_manager: PrivacyManager = None,
                 consent_manager: ConsentManager = None):
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        self.privacy_manager = privacy_manager or MockPrivacyManager()
        self.consent_manager = consent_manager or MockConsentManager()
        
    def process(self, text: str, user_id: str = "anonymous") -> NLPResult:
        """Process text through the full NLP pipeline"""
        # Check privacy budget
        budget = self.privacy_manager.check_privacy_budget(user_id)
        if not budget.has_budget():
            # Return limited result if budget exhausted
            return NLPResult(
                intent=IntentResult("PRIVACY_LIMIT", 1.0, 
                                  "You've reached your privacy limit for today. Please try again tomorrow."),
                entities=ExtractedEntities(),
                raw_text=text
            )
        
        # Use privacy budget
        budget.use_budget(1)
        
        # Recognize intent
        intent_result = self.intent_recognizer.recognize(text)
        
        # Extract entities
        entities = self.entity_extractor.extract(text)
        
        # Check consent for entity extraction
        if entities.skills and not self.consent_manager.check_consent(
            ConsentType.SHARE_SKILLS, "skill_matching"):
            entities.skills = []  # Clear if no consent
            
        if entities.locations and not self.consent_manager.check_consent(
            ConsentType.SHARE_LOCATION, "location_matching"):
            entities.locations = []  # Clear if no consent
        
        # Combine results
        return NLPResult(
            intent=intent_result,
            entities=entities,
            raw_text=text
        )
        
    def reset_context(self):
        """Reset conversation context"""
        self.intent_recognizer.reset_context()