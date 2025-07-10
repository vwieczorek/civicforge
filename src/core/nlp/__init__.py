"""NLP module for CivicForge"""

from .nlp_processor import NLPProcessor, NLPResult
from .intent_recognition import IntentRecognizer, IntentResult
from .entity_extraction import EntityExtractor, ExtractedEntities

__all__ = [
    'NLPProcessor', 
    'NLPResult',
    'IntentRecognizer',
    'IntentResult',
    'EntityExtractor',
    'ExtractedEntities'
]