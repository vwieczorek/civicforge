"""
Core Interfaces for CivicForge

Defines protocols and interfaces for the hybrid agent architecture,
preparing for future implementation of privacy, consent, and Local Controller.
"""

from .privacy_manager import PrivacyManager, PrivacyBudget
from .local_controller import LocalController, ApprovalRequest, ApprovalResponse
from .consent_manager import ConsentManager, ConsentRequest, ConsentRecord
from .llm_provider import LLMProvider, LLMResponse

__all__ = [
    "PrivacyManager",
    "PrivacyBudget",
    "LocalController", 
    "ApprovalRequest",
    "ApprovalResponse",
    "ConsentManager",
    "ConsentRequest",
    "ConsentRecord",
    "LLMProvider",
    "LLMResponse"
]