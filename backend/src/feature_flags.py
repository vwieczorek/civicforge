"""
Feature flag management for safe rollout of features
"""

import os
from typing import Optional, Dict, Any
from enum import Enum


class FeatureFlag(Enum):
    """Available feature flags"""
    REWARD_DISTRIBUTION = "reward_distribution"
    SIGNATURE_ATTESTATION = "signature_attestation"
    DISPUTE_RESOLUTION = "dispute_resolution"


class FeatureFlagManager:
    """
    Simple feature flag manager using environment variables.
    In production, this could be replaced with LaunchDarkly, Unleash, etc.
    """
    
    def __init__(self):
        self.stage = os.environ.get('STAGE', 'dev')
        self._flags_cache: Dict[str, Any] = {}
    
    def is_enabled(self, flag: FeatureFlag, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag: The feature flag to check
            user_id: Optional user ID for user-specific flags
            
        Returns:
            bool: True if feature is enabled
        """
        # Check environment variable first
        env_key = f"FF_{flag.value.upper()}"
        env_value = os.environ.get(env_key, "false").lower()
        
        # Special handling for gradual rollout
        if env_value == "internal":
            # Only enable for internal team (check user metadata)
            return self._is_internal_user(user_id)
        elif env_value.endswith("%"):
            # Percentage rollout
            percentage = int(env_value[:-1])
            return self._is_in_rollout_percentage(user_id, percentage)
        
        return env_value in ["true", "1", "yes", "on"]
    
    def _is_internal_user(self, user_id: Optional[str]) -> bool:
        """Check if user is part of internal team"""
        if not user_id:
            return False
        
        # In production, this would check user metadata or a whitelist
        internal_users = os.environ.get("INTERNAL_USERS", "").split(",")
        return user_id in internal_users
    
    def _is_in_rollout_percentage(self, user_id: Optional[str], percentage: int) -> bool:
        """Determine if user is in rollout percentage"""
        if not user_id or percentage <= 0:
            return False
        if percentage >= 100:
            return True
        
        # Simple hash-based rollout
        # In production, use a more sophisticated approach
        user_hash = hash(user_id) % 100
        return user_hash < percentage
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get status of all feature flags"""
        return {
            flag.value: self.is_enabled(flag)
            for flag in FeatureFlag
        }


# Global instance
feature_flags = FeatureFlagManager()