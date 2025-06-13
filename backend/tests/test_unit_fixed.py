"""
High-value unit tests extracted from legacy test_unit.py
TODO: Further refactor into module-specific test files
"""

import pytest
from unittest.mock import patch
from datetime import datetime
from src.models import Quest, QuestStatus, QuestCreate, QuestSubmission
from src.state_machine import QuestStateMachine
from src.signature import create_attestation_message
from src.feature_flags import FeatureFlag, feature_flags


class TestQuestStateMachine:
    """Tests for quest state transitions"""
    
    def test_can_user_claim(self):
        """Test user claim authorization logic"""
        quest = Quest(
            questId="q1",
            title="Test Quest",
            description="Test Description",
            status=QuestStatus.OPEN,
            creatorId="creator-123",
            performerId=None,
            rewardXp=100,
            rewardReputation=10,
            attestations=[],
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        # Creator cannot claim their own quest
        assert not QuestStateMachine.can_user_claim(quest, "creator-123")
        
        # Other users can claim open quests
        assert QuestStateMachine.can_user_claim(quest, "performer-456")
        
        # Cannot claim non-open quests
        quest.status = QuestStatus.CLAIMED
        assert not QuestStateMachine.can_user_claim(quest, "performer-789")
    
    def test_can_transition(self):
        """Test state transition validation"""
        # Valid transitions
        assert QuestStateMachine.can_transition(QuestStatus.OPEN, QuestStatus.CLAIMED)
        assert QuestStateMachine.can_transition(QuestStatus.CLAIMED, QuestStatus.SUBMITTED)
        assert QuestStateMachine.can_transition(QuestStatus.SUBMITTED, QuestStatus.COMPLETE)
        
        # Invalid transitions
        assert not QuestStateMachine.can_transition(QuestStatus.OPEN, QuestStatus.COMPLETE)
        assert not QuestStateMachine.can_transition(QuestStatus.COMPLETE, QuestStatus.OPEN)


class TestSignature:
    """Tests for cryptographic signature functions"""
    
    def test_create_attestation_message(self):
        """Test attestation message creation"""
        message = create_attestation_message(
            quest_id="quest-123",
            user_id="user-456",
            role="requestor"
        )
        
        expected = (
            "I am attesting to the completion of CivicForge Quest.\n"
            "Quest ID: quest-123\n"
            "My User ID: user-456\n"
            "My Role: requestor"
        )
        assert message == expected


class TestFeatureFlags:
    """Tests for feature flag functionality"""
    
    @patch.dict('os.environ', {'FF_DISPUTE_RESOLUTION': 'true'})
    def test_feature_flag_enabled(self):
        """Test feature flag when enabled"""
        # Create new instance to pick up env changes
        from src.feature_flags import FeatureFlagManager, FeatureFlag
        ff = FeatureFlagManager()
        assert ff.is_enabled(FeatureFlag.DISPUTE_RESOLUTION)
    
    def test_feature_flag_percentage(self):
        """Test percentage-based feature flags"""
        # Test 0% - should be disabled for all users
        with patch.dict('os.environ', {'FF_REWARD_DISTRIBUTION': '0%'}):
            from src.feature_flags import FeatureFlagManager, FeatureFlag
            ff = FeatureFlagManager()
            assert ff.is_enabled(FeatureFlag.REWARD_DISTRIBUTION, user_id="user-123") is False
            assert ff.is_enabled(FeatureFlag.REWARD_DISTRIBUTION, user_id="user-456") is False
        
        # Test 100% - should be enabled for all users
        with patch.dict('os.environ', {'FF_REWARD_DISTRIBUTION': '100%'}):
            ff2 = FeatureFlagManager()
            assert ff2.is_enabled(FeatureFlag.REWARD_DISTRIBUTION, user_id="user-123") is True
            assert ff2.is_enabled(FeatureFlag.REWARD_DISTRIBUTION, user_id="user-456") is True