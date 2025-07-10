"""
Privacy Manager Interface

Defines the protocol for privacy-preserving operations in CivicForge.
This will be implemented by the Local Controller in future phases.
"""

from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PrivacyBudget:
    """Tracks privacy budget to prevent user profiling"""
    total_queries: int = 100
    queries_used: int = 0
    reset_date: datetime = None
    
    def has_budget(self) -> bool:
        """Check if there's remaining privacy budget"""
        return self.queries_used < self.total_queries
    
    def use_budget(self, amount: int = 1) -> bool:
        """Use privacy budget, return True if successful"""
        if self.queries_used + amount <= self.total_queries:
            self.queries_used += amount
            return True
        return False


class PrivacyManager(Protocol):
    """
    Protocol for privacy management operations.
    
    Future implementations will handle:
    - Local data storage and processing
    - Differential privacy for queries
    - Data minimization
    - Consent enforcement
    """
    
    def check_privacy_budget(self, user_id: str) -> PrivacyBudget:
        """Check remaining privacy budget for a user"""
        ...
    
    def filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or redact sensitive information before sharing"""
        ...
    
    def can_share_data(self, data_type: str, purpose: str) -> bool:
        """Check if data can be shared for given purpose"""
        ...
    
    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize data while preserving utility"""
        ...
    
    def get_shareable_profile(self, user_id: str, purpose: str) -> Dict[str, Any]:
        """Get user profile data that can be shared for given purpose"""
        ...


class MockPrivacyManager:
    """
    Mock implementation for Phase 1 development.
    Always permits operations but logs them for future implementation.
    """
    
    def __init__(self):
        self._budgets = {}
        self._log = []
    
    def check_privacy_budget(self, user_id: str) -> PrivacyBudget:
        """Check remaining privacy budget for a user"""
        if user_id not in self._budgets:
            self._budgets[user_id] = PrivacyBudget()
        return self._budgets[user_id]
    
    def filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """For now, return data as-is but log the operation"""
        self._log.append(("filter_sensitive", data))
        # In future: remove emails, phone numbers, addresses, etc.
        return data
    
    def can_share_data(self, data_type: str, purpose: str) -> bool:
        """For now, always allow but log the request"""
        self._log.append(("can_share", data_type, purpose))
        return True
    
    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """For now, return data as-is but log the operation"""
        self._log.append(("anonymize", data))
        return data
    
    def get_shareable_profile(self, user_id: str, purpose: str) -> Dict[str, Any]:
        """Return minimal profile for now"""
        self._log.append(("get_profile", user_id, purpose))
        return {
            "user_id": f"anon_{hash(user_id) % 10000}",
            "interests": [],  # Would come from consent
            "availability": []  # Would come from consent
        }