"""
Intent Recognition V2 for CivicForge

Embedding-based intent recognition using sentence-transformers for real
semantic understanding. Maintains compatibility with existing tests while
providing foundation for future LLM integration.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class IntentResult:
    """Result of intent recognition"""
    intent: str
    confidence: float
    suggested_clarification: Optional[str] = None
    method: str = "embedding"  # Track if we used embedding or fallback


class EmbeddingIntentRecognizer:
    """Recognizes user intent using semantic embeddings"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Load pre-trained sentence transformer
        self.model = SentenceTransformer(model_name)
        
        # Intent exemplars - representative phrases for each intent
        self.intent_exemplars = {
            "OFFER_HELP": [
                "I want to help my community",
                "How can I volunteer?",
                "I'd like to contribute",
                "I want to make a difference",
                "Looking to volunteer my time",
                "I'd love to help out",
                "Where can I volunteer?",
                "I want to give back to my community"
            ],
            "REQUEST_HELP": [
                "We need help",
                "Looking for volunteers",
                "We need assistance",
                "Seeking volunteers for our event",
                "We require help with",
                "Volunteers needed",
                "Can someone help us",
                "We're looking for people to help"
            ],
            "SHARE_AVAILABILITY": [
                "I'm available on weekends",
                "I have time on Saturday",
                "I'm free in the evenings",
                "My schedule is open on",
                "I can help during",
                "I have availability",
                "I'm available to help",
                "My free time is"
            ],
            "SHARE_SKILLS": [
                "I'm good at teaching",
                "I have experience with",
                "I'm skilled in",
                "I can teach",
                "My expertise is in",
                "I'm a professional",
                "I know how to",
                "I'm experienced in"
            ]
        }
        
        # Pre-compute embeddings for all exemplars
        self.intent_embeddings = {}
        for intent, phrases in self.intent_exemplars.items():
            embeddings = self.model.encode(phrases)
            self.intent_embeddings[intent] = embeddings
            
        # Context tracking
        self.context = {}
        self.last_intent = None
        
        # Contextual patterns for yes/no responses
        self.contextual_patterns = {
            "CONFIRM_HELP": {
                "keywords": ["yes", "sure", "okay", "definitely", "absolutely"],
                "context_required": "OFFER_HELP"
            },
            "CONFIRM_INTEREST": {
                "keywords": ["yes", "interested", "tell me", "please"],
                "context_required": "REQUEST_HELP"
            }
        }
        
        # Confidence thresholds
        self.high_confidence_threshold = 0.75
        self.medium_confidence_threshold = 0.55
        self.low_confidence_threshold = 0.40

    def recognize(self, text: str) -> IntentResult:
        """Recognize intent from input text using embeddings"""
        # Normalize text
        text_lower = text.lower().strip()
        
        # First check contextual intents if we have context
        if self.last_intent and self._is_short_response(text_lower):
            contextual_result = self._check_contextual_intent(text_lower)
            if contextual_result:
                return contextual_result
        
        # Encode the input text
        text_embedding = self.model.encode([text])
        
        # Calculate similarities with all intent exemplars
        intent_scores = {}
        for intent, exemplar_embeddings in self.intent_embeddings.items():
            similarities = cosine_similarity(text_embedding, exemplar_embeddings)[0]
            # Use max similarity as the score for this intent
            intent_scores[intent] = float(np.max(similarities))
        
        # Find best match
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent, confidence = best_intent
        
        # Adjust confidence based on thresholds
        if confidence >= self.high_confidence_threshold:
            result = IntentResult(intent=intent, confidence=confidence)
        elif confidence >= self.medium_confidence_threshold:
            result = IntentResult(
                intent=intent, 
                confidence=confidence,
                suggested_clarification=self._get_clarification_for_intent(intent)
            )
        elif confidence >= self.low_confidence_threshold:
            # Low confidence - might be the intent but need confirmation
            result = IntentResult(
                intent=intent,
                confidence=confidence,
                suggested_clarification="I think you might want to " + self._get_intent_description(intent) + ". Is that correct?"
            )
        else:
            # Very low confidence - unclear
            result = IntentResult(
                intent="UNCLEAR",
                confidence=confidence,
                suggested_clarification="I'm not sure what you mean. Are you looking to help, or do you need assistance?"
            )
        
        # Update context
        self.last_intent = result.intent
        self.context["last_intent"] = result.intent
        
        return result
    
    def _is_short_response(self, text: str) -> bool:
        """Check if the response is short (likely yes/no/maybe)"""
        return len(text.split()) <= 3
    
    def _check_contextual_intent(self, text: str) -> Optional[IntentResult]:
        """Check for contextual intents based on conversation history"""
        for intent, pattern in self.contextual_patterns.items():
            if pattern.get("context_required") == self.last_intent:
                if any(keyword in text for keyword in pattern["keywords"]):
                    return IntentResult(intent=intent, confidence=0.8, method="contextual")
        return None
    
    def _get_intent_description(self, intent: str) -> str:
        """Get a human-readable description of the intent"""
        descriptions = {
            "OFFER_HELP": "volunteer or help your community",
            "REQUEST_HELP": "find volunteers or get help",
            "SHARE_AVAILABILITY": "share when you're available",
            "SHARE_SKILLS": "tell us about your skills"
        }
        return descriptions.get(intent, "engage with your community")
    
    def _get_clarification_for_intent(self, intent: str) -> str:
        """Get appropriate clarification question for medium confidence"""
        clarifications = {
            "OFFER_HELP": "Great! To help you volunteer, could you tell me what skills you have or when you're available?",
            "REQUEST_HELP": "I understand you need assistance. What kind of help are you looking for?",
            "SHARE_AVAILABILITY": "Thank you for sharing your availability. What kinds of activities interest you?",
            "SHARE_SKILLS": "Wonderful! When are you available to use these skills?"
        }
        return clarifications.get(intent, "Could you tell me more about what you're looking for?")
    
    def add_training_phrases(self, intent: str, phrases: List[str]):
        """Add new training phrases for an intent (for future learning)"""
        if intent not in self.intent_exemplars:
            self.intent_exemplars[intent] = []
        
        self.intent_exemplars[intent].extend(phrases)
        
        # Re-compute embeddings for this intent
        all_phrases = self.intent_exemplars[intent]
        self.intent_embeddings[intent] = self.model.encode(all_phrases)
    
    def reset_context(self):
        """Reset conversation context"""
        self.context = {}
        self.last_intent = None


# Backward compatibility wrapper
class IntentRecognizer(EmbeddingIntentRecognizer):
    """
    Wrapper class that maintains backward compatibility with existing code
    while using the new embedding-based approach
    """
    
    def __init__(self):
        # Initialize with a lightweight model
        super().__init__(model_name="all-MiniLM-L6-v2")
        
        # Keep the old pattern data for potential fallback
        self.intent_patterns = {
            "OFFER_HELP": {
                "keywords": ["help", "volunteer", "contribute", "assist", "support", "serve"],
                "phrases": ["want to help", "like to help", "can i volunteer"]
            },
            "REQUEST_HELP": {
                "keywords": ["need", "looking", "seeking", "require", "wanted"],
                "phrases": ["need help", "looking for volunteers", "we need"]
            },
            "SHARE_AVAILABILITY": {
                "keywords": ["free", "available", "can help"],
                "phrases": ["i'm free", "available on", "can help on"],
                "time_indicators": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            },
            "SHARE_SKILLS": {
                "keywords": ["good", "know", "teach", "expert", "experienced"],
                "phrases": ["good at", "know how to", "i can teach"]
            }
        }