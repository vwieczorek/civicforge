"""
Tests for the failed rewards reprocessing Lambda function
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import os

from botocore.exceptions import ClientError
from src.triggers.reprocess_failed_rewards import (
    handler,
    acquire_lease,
    release_lease,
    process_reward_with_lease,
    is_reward_already_processed,
    award_rewards_idempotently,
    update_reward_status
)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up environment variables for tests"""
    monkeypatch.setenv('USERS_TABLE', 'test-users-table')
    monkeypatch.setenv('FAILED_REWARDS_TABLE', 'test-failed-rewards-table')
    monkeypatch.setenv('MAX_RETRY_ATTEMPTS', '5')
    monkeypatch.setenv('LEASE_DURATION_SECONDS', '300')
    monkeypatch.setenv('AWS_LAMBDA_REQUEST_ID', 'test-request-123')


@pytest.fixture
def mock_tables(mocker):
    """Mock DynamoDB tables"""
    mock_users_table = MagicMock()
    mock_failed_rewards_table = MagicMock()
    
    mocker.patch('src.triggers.reprocess_failed_rewards.users_table', mock_users_table)
    mocker.patch('src.triggers.reprocess_failed_rewards.failed_rewards_table', mock_failed_rewards_table)
    
    return mock_users_table, mock_failed_rewards_table


@pytest.fixture
def sample_failed_reward():
    """Sample failed reward item"""
    return {
        'rewardId': 'reward-123',
        'userId': 'user-456',
        'questId': 'quest-789',
        'xpAmount': 100,
        'reputationAmount': 10,
        'questPointsAmount': 1,
        'retryCount': 0,
        'status': 'pending',
        'createdAt': datetime.now(timezone.utc).isoformat()
    }


class TestHandler:
    """Test the main handler function"""
    
    def test_handler_happy_path(self, mock_tables, sample_failed_reward, mocker):
        """Test successful processing of failed rewards"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock the query response
        mock_failed_rewards_table.query.return_value = {
            'Items': [sample_failed_reward]
        }
        
        # Mock successful lease acquisition
        mocker.patch('src.triggers.reprocess_failed_rewards.acquire_lease', return_value=True)
        
        # Mock successful processing
        mocker.patch('src.triggers.reprocess_failed_rewards.process_reward_with_lease', return_value='succeeded')
        
        # Call handler
        result = handler({}, {})
        
        # Assertions
        assert result['processed'] == 1
        assert result['succeeded'] == 1
        assert result['failed'] == 0
        assert result['abandoned'] == 0
        assert result['skipped'] == 0
        
        # Verify query was made
        mock_failed_rewards_table.query.assert_called_once()
        
    def test_handler_lease_conflict(self, mock_tables, sample_failed_reward, mocker):
        """Test handling of lease conflicts"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock the query response
        mock_failed_rewards_table.query.return_value = {
            'Items': [sample_failed_reward]
        }
        
        # Mock failed lease acquisition
        mocker.patch('src.triggers.reprocess_failed_rewards.acquire_lease', return_value=False)
        
        # Call handler
        result = handler({}, {})
        
        # Assertions
        assert result['processed'] == 1
        assert result['succeeded'] == 0
        assert result['failed'] == 0
        assert result['abandoned'] == 0
        assert result['skipped'] == 1
        
    def test_handler_processing_error(self, mock_tables, sample_failed_reward, mocker):
        """Test handling of processing errors"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock the query response
        mock_failed_rewards_table.query.return_value = {
            'Items': [sample_failed_reward]
        }
        
        # Mock successful lease acquisition
        mocker.patch('src.triggers.reprocess_failed_rewards.acquire_lease', return_value=True)
        
        # Mock processing error
        mocker.patch('src.triggers.reprocess_failed_rewards.process_reward_with_lease', side_effect=Exception("Processing error"))
        
        # Mock release lease
        mock_release = mocker.patch('src.triggers.reprocess_failed_rewards.release_lease')
        
        # Call handler
        result = handler({}, {})
        
        # Assertions
        assert result['processed'] == 1
        assert result['succeeded'] == 0
        assert result['failed'] == 1
        assert result['abandoned'] == 0
        assert result['skipped'] == 0
        
        # Verify lease was released on error
        mock_release.assert_called_once_with('reward-123')


class TestLeaseManagement:
    """Test lease acquisition and release functions"""
    
    def test_acquire_lease_success(self, mock_tables):
        """Test successful lease acquisition"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        current_time = datetime.now(timezone.utc)
        
        # Mock successful update
        mock_failed_rewards_table.update_item.return_value = {}
        
        result = acquire_lease('reward-123', current_time)
        
        assert result is True
        mock_failed_rewards_table.update_item.assert_called_once()
        
        # Verify the update expression
        call_args = mock_failed_rewards_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'rewardId': 'reward-123'}
        assert 'leaseOwner' in call_args.kwargs['UpdateExpression']
        assert 'leaseExpiresAt' in call_args.kwargs['UpdateExpression']
        
    def test_acquire_lease_already_leased(self, mock_tables):
        """Test lease acquisition when already leased"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        current_time = datetime.now(timezone.utc)
        
        # Mock conditional check failure
        error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        mock_failed_rewards_table.update_item.side_effect = error
        
        result = acquire_lease('reward-123', current_time)
        
        assert result is False
        
    def test_release_lease(self, mock_tables):
        """Test lease release"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        release_lease('reward-123')
        
        mock_failed_rewards_table.update_item.assert_called_once()
        call_args = mock_failed_rewards_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'rewardId': 'reward-123'}
        assert 'REMOVE leaseOwner, leaseExpiresAt' in call_args.kwargs['UpdateExpression']


class TestRewardProcessing:
    """Test reward processing logic"""
    
    def test_process_reward_max_retries_exceeded(self, mock_tables, sample_failed_reward, mocker):
        """Test abandonment when max retries exceeded"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Set retry count to max
        sample_failed_reward['retryCount'] = 5
        
        # Mock update status
        mock_update = mocker.patch('src.triggers.reprocess_failed_rewards.update_reward_status')
        
        current_time = datetime.now(timezone.utc)
        result = process_reward_with_lease(sample_failed_reward, current_time)
        
        assert result == 'abandoned'
        mock_update.assert_called_once_with('reward-123', 'abandoned', 5)
        
    def test_process_reward_already_processed(self, mock_tables, sample_failed_reward, mocker):
        """Test handling of already processed rewards"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock already processed check
        mocker.patch('src.triggers.reprocess_failed_rewards.is_reward_already_processed', return_value=True)
        
        # Mock update status
        mock_update = mocker.patch('src.triggers.reprocess_failed_rewards.update_reward_status')
        
        current_time = datetime.now(timezone.utc)
        result = process_reward_with_lease(sample_failed_reward, current_time)
        
        assert result == 'succeeded'
        mock_update.assert_called_once_with('reward-123', 'resolved', 0)
        
    def test_process_reward_success(self, mock_tables, sample_failed_reward, mocker):
        """Test successful reward processing"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock not already processed
        mocker.patch('src.triggers.reprocess_failed_rewards.is_reward_already_processed', return_value=False)
        
        # Mock successful award
        mocker.patch('src.triggers.reprocess_failed_rewards.award_rewards_idempotently', return_value=True)
        
        # Mock update status
        mock_update = mocker.patch('src.triggers.reprocess_failed_rewards.update_reward_status')
        
        current_time = datetime.now(timezone.utc)
        result = process_reward_with_lease(sample_failed_reward, current_time)
        
        assert result == 'succeeded'
        mock_update.assert_called_once_with('reward-123', 'resolved', 1)
        
    def test_process_reward_failure(self, mock_tables, sample_failed_reward, mocker):
        """Test failed reward processing"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock not already processed
        mocker.patch('src.triggers.reprocess_failed_rewards.is_reward_already_processed', return_value=False)
        
        # Mock failed award
        mocker.patch('src.triggers.reprocess_failed_rewards.award_rewards_idempotently', return_value=False)
        
        # Mock update status
        mock_update = mocker.patch('src.triggers.reprocess_failed_rewards.update_reward_status')
        
        current_time = datetime.now(timezone.utc)
        result = process_reward_with_lease(sample_failed_reward, current_time)
        
        assert result == 'failed'
        mock_update.assert_called_once_with('reward-123', 'pending', 1)


class TestIdempotency:
    """Test idempotency mechanisms"""
    
    def test_is_reward_already_processed_true(self, mock_tables):
        """Test checking if reward is already processed"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock user with processed reward
        mock_users_table.get_item.return_value = {
            'Item': {
                'userId': 'user-456',
                'processedRewardIds': {'reward-123', 'reward-456'}
            }
        }
        
        result = is_reward_already_processed('user-456', 'reward-123')
        
        assert result is True
        
    def test_is_reward_already_processed_false(self, mock_tables):
        """Test checking if reward is not processed"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock user without this reward
        mock_users_table.get_item.return_value = {
            'Item': {
                'userId': 'user-456',
                'processedRewardIds': {'reward-456'}
            }
        }
        
        result = is_reward_already_processed('user-456', 'reward-123')
        
        assert result is False
        
    def test_is_reward_already_processed_no_user(self, mock_tables):
        """Test checking reward for non-existent user"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock no user found
        mock_users_table.get_item.return_value = {}
        
        result = is_reward_already_processed('user-456', 'reward-123')
        
        assert result is False
        
    def test_award_rewards_idempotently_success(self, mock_tables):
        """Test successful idempotent reward awarding"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock successful update
        mock_users_table.update_item.return_value = {}
        
        result = award_rewards_idempotently(
            user_id='user-456',
            reward_id='reward-123',
            xp_amount=100,
            reputation_amount=10,
            quest_points_amount=1
        )
        
        assert result is True
        
        # Verify update was called with correct parameters
        call_args = mock_users_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'userId': 'user-456'}
        assert 'experience = experience + :xp' in call_args.kwargs['UpdateExpression']
        assert 'reputation = reputation + :rep' in call_args.kwargs['UpdateExpression']
        assert 'processedRewardIds' in call_args.kwargs['UpdateExpression']
        
    def test_award_rewards_idempotently_already_processed(self, mock_tables):
        """Test idempotent handling of already processed rewards"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Mock conditional check failure
        error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        mock_users_table.update_item.side_effect = error
        
        result = award_rewards_idempotently(
            user_id='user-456',
            reward_id='reward-123',
            xp_amount=100,
            reputation_amount=10,
            quest_points_amount=1
        )
        
        # Should return True even though it was already processed
        assert result is True


class TestUpdateRewardStatus:
    """Test reward status updates"""
    
    def test_update_reward_status_pending(self, mock_tables):
        """Test updating reward to pending status"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        update_reward_status('reward-123', 'pending', 1)
        
        call_args = mock_failed_rewards_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'rewardId': 'reward-123'}
        assert ':status' in call_args.kwargs['ExpressionAttributeValues']
        assert call_args.kwargs['ExpressionAttributeValues'][':status'] == 'pending'
        assert call_args.kwargs['ExpressionAttributeValues'][':count'] == 1
        
    def test_update_reward_status_resolved(self, mock_tables):
        """Test updating reward to resolved status"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        update_reward_status('reward-123', 'resolved', 2)
        
        call_args = mock_failed_rewards_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'rewardId': 'reward-123'}
        assert ':status' in call_args.kwargs['ExpressionAttributeValues']
        assert call_args.kwargs['ExpressionAttributeValues'][':status'] == 'resolved'
        assert ':resolved_at' in call_args.kwargs['ExpressionAttributeValues']
        assert 'resolvedAt' in call_args.kwargs['UpdateExpression']
        
    def test_update_reward_status_abandoned(self, mock_tables):
        """Test updating reward to abandoned status"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        update_reward_status('reward-123', 'abandoned', 5)
        
        call_args = mock_failed_rewards_table.update_item.call_args
        assert call_args.kwargs['Key'] == {'rewardId': 'reward-123'}
        assert call_args.kwargs['ExpressionAttributeValues'][':status'] == 'abandoned'
        assert ':resolved_at' in call_args.kwargs['ExpressionAttributeValues']
        assert 'leaseOwner = :none' in call_args.kwargs['UpdateExpression']


class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_full_retry_cycle(self, mock_tables, sample_failed_reward, mocker):
        """Test a full retry cycle from pending to resolved"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # First attempt - simulate failure
        mock_failed_rewards_table.query.return_value = {'Items': [sample_failed_reward]}
        mocker.patch('src.triggers.reprocess_failed_rewards.acquire_lease', return_value=True)
        mocker.patch('src.triggers.reprocess_failed_rewards.is_reward_already_processed', return_value=False)
        mocker.patch('src.triggers.reprocess_failed_rewards.award_rewards_idempotently', return_value=False)
        mock_update = mocker.patch('src.triggers.reprocess_failed_rewards.update_reward_status')
        
        result1 = handler({}, {})
        assert result1['failed'] == 1
        mock_update.assert_called_with('reward-123', 'pending', 1)
        
        # Second attempt - simulate success
        sample_failed_reward['retryCount'] = 1
        mocker.patch('src.triggers.reprocess_failed_rewards.award_rewards_idempotently', return_value=True)
        
        result2 = handler({}, {})
        assert result2['succeeded'] == 1
        mock_update.assert_called_with('reward-123', 'resolved', 2)
        
    def test_concurrent_processing_protection(self, mock_tables, mocker):
        """Test that concurrent processing is prevented by lease system"""
        mock_users_table, mock_failed_rewards_table = mock_tables
        
        # Create two reward items
        rewards = [
            {'rewardId': 'reward-1', 'userId': 'user-1', 'status': 'pending', 'retryCount': 0},
            {'rewardId': 'reward-2', 'userId': 'user-2', 'status': 'pending', 'retryCount': 0}
        ]
        
        mock_failed_rewards_table.query.return_value = {'Items': rewards}
        
        # First reward gets lease, second doesn't
        acquire_lease_mock = mocker.patch('src.triggers.reprocess_failed_rewards.acquire_lease')
        acquire_lease_mock.side_effect = [True, False]
        
        mocker.patch('src.triggers.reprocess_failed_rewards.process_reward_with_lease', return_value='succeeded')
        
        result = handler({}, {})
        
        assert result['processed'] == 2
        assert result['succeeded'] == 1
        assert result['skipped'] == 1