"""
NLP Processor for CivicForge

Combines intent recognition and entity extraction to provide
comprehensive natural language understanding.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict

from .intent_recognition import IntentRecognizer, IntentResult
from .entity_extraction import EntityExtractor, ExtractedEntities


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
    
    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        
    def process(self, text: str) -> NLPResult:
        """Process text through the full NLP pipeline"""
        # Recognize intent
        intent_result = self.intent_recognizer.recognize(text)
        
        # Extract entities
        entities = self.entity_extractor.extract(text)
        
        # Combine results
        return NLPResult(
            intent=intent_result,
            entities=entities,
            raw_text=text
        )
        
    def reset_context(self):
        """Reset conversation context"""
        self.intent_recognizer.reset_context()