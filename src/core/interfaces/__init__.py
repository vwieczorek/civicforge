"""
Core Interfaces for CivicForge

Defines protocols and interfaces for the hybrid agent architecture,
preparing for future implementation of privacy, consent, and Local Controller.
"""

from .privacy_manager import PrivacyManager, PrivacyBudget, MockPrivacyManager
from .local_controller import LocalController, ApprovalRequest, ApprovalResponse, ActionType, MockLocalController
from .consent_manager import ConsentManager, ConsentRequest, ConsentRecord, ConsentType, MockConsentManager
from .llm_provider import LLMProvider, LLMResponse, MockLLMProvider

__all__ = [
    "PrivacyManager",
    "PrivacyBudget",
    "MockPrivacyManager",
    "LocalController", 
    "ApprovalRequest",
    "ApprovalResponse",
    "ActionType",
    "MockLocalController",
    "ConsentManager",
    "ConsentRequest",
    "ConsentRecord",
    "ConsentType",
    "MockConsentManager",
    "LLMProvider",
    "LLMResponse",
    "MockLLMProvider"
]