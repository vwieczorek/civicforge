"""
Intent Recognition for CivicForge

Enhanced with embedding-based semantic understanding while maintaining
backward compatibility with existing pattern-based tests.
"""

from dataclasses import dataclass
from typing import Optional, Dict
import warnings


@dataclass
class IntentResult:
    """Result of intent recognition"""
    intent: str
    confidence: float
    suggested_clarification: Optional[str] = None


class IntentRecognizer:
    """Recognizes user intent from natural language input"""

    def __init__(self):
        # Try to use the embedding-based recognizer
        try:
            from .intent_recognition_v2 import EmbeddingIntentRecognizer
            self._impl = EmbeddingIntentRecognizer()
            self._using_embeddings = True
        except ImportError:
            warnings.warn(
                "sentence-transformers not installed. Falling back to pattern matching. "
                "Install with: pip install sentence-transformers",
                UserWarning
            )
            self._impl = None
            self._using_embeddings = False
            self._init_pattern_matching()
    
    def _init_pattern_matching(self):
        """Initialize pattern-based matching as fallback"""
        self.context = {}
        self.last_intent = None
        
        # Intent patterns - keywords and phrases that indicate each intent
        self.intent_patterns = {
            "OFFER_HELP": {
                "keywords": [
                    "help", "volunteer", "contribute", "assist", "support", "serve",
                ],
                "phrases": [
                    "want to help", "like to help", "can i volunteer",
                    "how can i volunteer", "like to contribute", "time to help",
                    "what needs doing", "how can i help", "want to volunteer",
                    "i'd love to volunteer", "i would love to help", "love to help"
                ],
            },
            "REQUEST_HELP": {
                "keywords": ["need", "looking", "seeking", "require", "wanted"],
                "phrases": [
                    "need help", "looking for volunteers", "we need",
                    "seeking volunteers", "need people", "seeking tutors",
                    "looking for help", "volunteers needed",
                ],
            },
            "SHARE_AVAILABILITY": {
                "keywords": ["free", "available", "can help"],
                "phrases": [
                    "i'm free", "i am free", "available on", "can help on",
                    "have time", "evenings available", "mornings available",
                    "can help saturday", "can help sunday", "tuesday evenings",
                    "i have",
                ],
                "time_indicators": [
                    "monday", "tuesday", "wednesday", "thursday", "friday",
                    "saturday", "sunday", "weekend", "weekday", "morning",
                    "afternoon", "evening", "night",
                ],
            },
            "SHARE_SKILLS": {
                "keywords": ["good", "know", "teach", "expert", "experienced"],
                "phrases": [
                    "good at", "know how to", "i can teach", "i can help with",
                    "i'm a", "i am a", "master gardener", "experienced in",
                ],
            },
        }
        
        # Additional contextual intents
        self.contextual_patterns = {
            "CONFIRM_HELP": {
                "keywords": ["yes", "sure", "okay", "definitely"],
                "context_required": "OFFER_HELP"
            },
            "CONFIRM_INTEREST": {
                "keywords": ["yes", "interested", "tell me"],
                "context_required": "REQUEST_HELP"
            }
        }

    def recognize(self, text: str) -> IntentResult:
        """Recognize intent from input text"""
        if self._using_embeddings:
            return self._impl.recognize(text)
        else:
            return self._pattern_based_recognize(text)
    
    def _pattern_based_recognize(self, text: str) -> IntentResult:
        """Fallback pattern-based recognition"""
        # Normalize text
        text_lower = text.lower().strip()

        # First check contextual intents if we have context
        if self.last_intent and text_lower in ["yes", "no", "maybe", "sure", "okay"]:
            contextual_result = self._check_contextual_intent(text_lower)
            if contextual_result:
                return contextual_result

        # Score each intent
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = self._calculate_intent_score(text_lower, patterns)
            intent_scores[intent] = score

        # Find best match
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent, confidence = best_intent

        # Handle unclear cases
        if confidence < 0.5:
            result = IntentResult(
                intent="UNCLEAR",
                confidence=confidence,
                suggested_clarification="I'm not sure what you mean. Are you looking to help, or do you need assistance?",
            )
        else:
            result = IntentResult(intent=intent, confidence=confidence)
            
        # Update context
        self.last_intent = result.intent
        self.context["last_intent"] = result.intent
        
        return result

    def _calculate_intent_score(self, text: str, patterns: Dict) -> float:
        """Calculate confidence score for a specific intent"""
        score = 0.0

        # Check keywords
        keywords = patterns.get("keywords", [])
        keyword_matches = sum(1 for kw in keywords if kw in text)
        if keywords:
            score += (keyword_matches / len(keywords)) * 0.4

        # Check phrases (weighted more heavily)
        phrases = patterns.get("phrases", [])
        phrase_matches = sum(1 for phrase in phrases if phrase in text)
        if phrases and phrase_matches > 0:
            # Give high score if we match a phrase exactly
            score += 0.75

        # Special handling for availability - check for time indicators
        if "time_indicators" in patterns:
            time_indicators = patterns["time_indicators"]
            time_matches = sum(1 for indicator in time_indicators if indicator in text)
            if time_matches > 0:
                score += 0.3

        # Boost score if we have both phrase and keyword matches
        if phrase_matches > 0 and keyword_matches > 0:
            score = min(score * 1.1, 1.0)

        return min(score, 1.0)

    def _check_contextual_intent(self, text: str) -> Optional[IntentResult]:
        """Check for contextual intents based on conversation history"""
        for intent, pattern in self.contextual_patterns.items():
            if pattern.get("context_required") == self.last_intent:
                if any(keyword in text for keyword in pattern["keywords"]):
                    return IntentResult(intent=intent, confidence=0.8)
        return None

    def reset_context(self):
        """Reset conversation context"""
        if self._using_embeddings:
            self._impl.reset_context()
        else:
            self.context = {}
            self.last_intent = None