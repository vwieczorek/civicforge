"""
Intent Recognition for CivicForge

Simple pattern-based intent recognition following the "start simple"
philosophy. Identifies user intentions in civic engagement conversations.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class IntentResult:
    """Result of intent recognition"""

    intent: str
    confidence: float
    suggested_clarification: Optional[str] = None


class IntentRecognizer:
    """Recognizes user intent from natural language input"""

    def __init__(self):
        # Intent patterns - keywords and phrases that indicate each intent
        self.intent_patterns = {
            "OFFER_HELP": {
                "keywords": [
                    "help",
                    "volunteer",
                    "contribute",
                    "assist",
                    "support",
                    "serve",
                ],
                "phrases": [
                    "want to help",
                    "like to help",
                    "can i volunteer",
                    "how can i volunteer",
                    "like to contribute",
                    "time to help",
                    "what needs doing",
                    "how can i help",
                    "want to volunteer",
                ],
            },
            "REQUEST_HELP": {
                "keywords": ["need", "looking", "seeking", "require", "wanted"],
                "phrases": [
                    "need help",
                    "looking for volunteers",
                    "we need",
                    "seeking volunteers",
                    "need people",
                    "seeking tutors",
                    "looking for help",
                    "volunteers needed",
                ],
            },
            "SHARE_AVAILABILITY": {
                "keywords": ["free", "available", "can help"],
                "phrases": [
                    "i'm free",
                    "i am free",
                    "available on",
                    "can help on",
                    "have time",
                    "evenings available",
                    "mornings available",
                    "can help saturday",
                    "can help sunday",
                    "tuesday evenings",
                    "i have",
                ],
                "time_indicators": [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                    "weekend",
                    "weekday",
                    "morning",
                    "afternoon",
                    "evening",
                    "night",
                ],
            },
            "SHARE_SKILLS": {
                "keywords": ["good", "know", "teach", "expert", "experienced"],
                "phrases": [
                    "good at",
                    "know how to",
                    "i can teach",
                    "i can help with",
                    "i'm a",
                    "i am a",
                    "master gardener",
                    "experienced in",
                ],
            },
        }

        self.context = {}

    def recognize(self, text: str) -> IntentResult:
        """Recognize intent from input text"""
        # Normalize text
        text_lower = text.lower().strip()

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
            return IntentResult(
                intent="UNCLEAR",
                confidence=confidence,
                suggested_clarification="I'm not sure what you mean. Are you looking to help, or do you need assistance?",
            )

        return IntentResult(intent=intent, confidence=confidence)

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

    def reset_context(self):
        """Reset conversation context"""
        self.context = {}
