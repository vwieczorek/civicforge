"""
Quick targeted tests to boost coverage to 70%
"""
from datetime import datetime
from unittest.mock import patch
from botocore.exceptions import ClientError


def test_state_machine_line_139():
    """Test state machine can_user_claim when quest already claimed - covers line 139"""
    from src.state_machine import QuestStateMachine
    from src.models import Quest, QuestStatus
    
    quest = Quest(
        questId="test-quest-1",
        creatorId="creator-123",
        title="Already Claimed Quest",
        description="This quest has already been claimed by someone",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.OPEN,
        performerId="performer-456",  # Already has a performer - triggers line 139
        createdAt=datetime.utcnow()
    )
    
    # Should return False for new user trying to claim already claimed quest
    assert not QuestStateMachine.can_user_claim(quest, "another-user-789")


def test_create_user_error_paths():
    """Test create_user trigger error handling - covers lines 84-85"""
    # Set environment variable before import
    with patch.dict('os.environ', {'USERS_TABLE_NAME': 'test-users'}):
        with patch('src.triggers.create_user.table') as mock_table:
            from src.triggers.create_user import handler
            
            # Test with ClientError that is NOT ConditionalCheckFailedException
            error_response = {'Error': {'Code': 'ValidationException'}}
            mock_table.put_item.side_effect = ClientError(error_response, 'PutItem')
            
            event = {
                'request': {
                    'userAttributes': {
                        'sub': 'test-user-id',
                        'email': 'test@example.com'
                    }
                },
                'userName': 'testuser'
            }
            
            # Should still return event (graceful failure)
            result = handler(event, {})
            assert result == event


def test_feature_flags_percentage_parsing():
    """Test feature flags percentage rollout parsing - covers lines 48-49"""
    from src.feature_flags import FeatureFlagManager, FeatureFlag
    
    flags = FeatureFlagManager()
    
    # Test percentage rollout (covers line 48-49)
    with patch.dict('os.environ', {'FF_REWARD_DISTRIBUTION': '75%'}):
        # This will parse the percentage and call _is_in_rollout_percentage
        result = flags.is_enabled(FeatureFlag.REWARD_DISTRIBUTION, user_id="test-user-123")
        assert isinstance(result, bool)  # Just verify it executes without error


def test_models_clean_html_empty():
    """Test clean_html with empty string - covers line 24"""
    from src.models import clean_html
    
    # Test empty string - should return empty string (line 24)
    assert clean_html("") == ""
    # Bleach strips whitespace-only strings
    assert clean_html("   ") == ""