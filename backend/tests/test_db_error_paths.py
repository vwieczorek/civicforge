"""
Comprehensive tests for database error paths and resilience.
Focuses on critical error scenarios identified in coverage gaps.
"""

import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from botocore.exceptions import ClientError

from src.db import get_db_client, DynamoDBClient
from src.models import Quest, QuestStatus, User, Attestation


@pytest.fixture
async def db_client():
    """Create a DynamoDB client for testing"""
    # Set test environment
    os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:8000'
    os.environ['QUESTS_TABLE_NAME'] = 'test-quests'
    os.environ['USERS_TABLE_NAME'] = 'test-users'
    os.environ['FAILED_REWARDS_TABLE_NAME'] = 'test-failed-rewards'
    
    db = DynamoDBClient()
    return db


class TestAtomicOperationErrors:
    """Test error handling in atomic operations"""
    
    @pytest.mark.asyncio
    async def test_claim_quest_atomic_conditional_check_failure(self, db_client):
        """Verify claim_quest_atomic returns False on ConditionalCheckFailedException"""
        # Create a mock client
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Condition not met'}},
            'UpdateItem'
        )
        
        # Create a mock async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should return False, not raise exception
            result = await db_client.claim_quest_atomic("quest-123", "user-456")
            assert result is False
            mock_dynamodb_client.update_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_claim_quest_atomic_generic_error_propagates(self, db_client):
        """Verify claim_quest_atomic propagates non-conditional errors"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Throttled'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should raise the exception
            with pytest.raises(ClientError) as exc_info:
                await db_client.claim_quest_atomic("quest-123", "user-456")
            
            assert exc_info.value.response['Error']['Code'] == 'ProvisionedThroughputExceededException'
    
    @pytest.mark.asyncio
    async def test_submit_quest_atomic_conditional_check_failure(self, db_client):
        """Verify submit_quest_atomic returns False when conditions not met"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.submit_quest_atomic("quest-123", "user-456", "Completed work")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_add_attestation_atomic_all_error_paths(self, db_client):
        """Test all error scenarios for add_attestation_atomic"""
        attestation = {
            'user_id': 'user-123',
            'role': 'requestor',
            'attested_at': datetime.now(timezone.utc).isoformat(),
            'signature': '0xabc123'
        }
        
        # Test 1: ConditionalCheckFailedException (duplicate attestation)
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.add_attestation_atomic("quest-123", attestation)
            assert result is False
        
        # Test 2: Generic error propagation
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException'}},
            'UpdateItem'
        )
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            with pytest.raises(ClientError):
                await db_client.add_attestation_atomic("quest-123", attestation)
    
    @pytest.mark.asyncio
    async def test_complete_quest_atomic_invalid_state(self, db_client):
        """Test completing quest in invalid state returns False"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.complete_quest_atomic("quest-123")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_quest_atomic_unauthorized(self, db_client):
        """Test delete by wrong user or wrong status returns False"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.delete_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'DeleteItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.delete_quest_atomic("quest-123", "wrong-user")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_dispute_quest_atomic_invalid_conditions(self, db_client):
        """Test dispute with invalid conditions returns False"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.dispute_quest_atomic("quest-123", "user-123", "Invalid dispute")
            assert result is False


class TestResourceManagementErrors:
    """Test error handling in resource management operations"""
    
    @pytest.mark.asyncio
    async def test_deduct_quest_creation_points_insufficient_balance(self, db_client):
        """Test deducting points with insufficient balance returns False"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.deduct_quest_creation_points("user-123")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_deduct_quest_creation_points_generic_error(self, db_client):
        """Test generic errors are propagated"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError'}},
            'UpdateItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            with pytest.raises(ClientError):
                await db_client.deduct_quest_creation_points("user-123")


class TestCriticalRewardFailureHandling:
    """Test the critical reward failure and recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_award_rewards_tracks_failure_on_error(self, db_client):
        """Test award_rewards tracks failures when main update fails"""
        # Enable failed rewards tracking
        db_client.failed_rewards_table_name = "test-failed-rewards"
        
        # Create mocks
        mock_dynamodb_client = AsyncMock()
        
        # First call to update_item (awarding) fails
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Database error'}},
            'UpdateItem'
        )
        
        # Second call to put_item (tracking failure) should succeed
        mock_dynamodb_client.put_item = AsyncMock(return_value={'ResponseMetadata': {'HTTPStatusCode': 200}})
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should raise the original error after tracking
            with pytest.raises(ClientError) as exc_info:
                await db_client.award_rewards(
                    user_id="test-user-123",
                    xp=100,
                    reputation=50,
                    quest_id="test-quest-456"
                )
            
            # Verify the failure was tracked
            mock_dynamodb_client.put_item.assert_called_once()
            call_args = mock_dynamodb_client.put_item.call_args[1]
            
            # Verify tracking data
            assert call_args['TableName'] == "test-failed-rewards"
            assert call_args['Item']['userId']['S'] == "test-user-123"
            assert call_args['Item']['questId']['S'] == "test-quest-456"
            assert call_args['Item']['xp']['N'] == "100"
            assert call_args['Item']['reputation']['N'] == "50"
            assert call_args['Item']['status']['S'] == "pending"
            assert 'recordId' in call_args['Item']
            assert 'createdAt' in call_args['Item']
            assert 'error' in call_args['Item']
    
    @pytest.mark.asyncio
    async def test_award_rewards_handles_double_failure(self, db_client):
        """Test when both reward and tracking fail"""
        db_client.failed_rewards_table_name = "test-failed-rewards"
        
        mock_dynamodb_client = AsyncMock()
        
        # Both operations fail
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError'}},
            'UpdateItem'
        )
        mock_dynamodb_client.put_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError'}},
            'PutItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should raise the original error even if tracking fails
            with pytest.raises(ClientError):
                await db_client.award_rewards(
                    user_id="test-user-123",
                    xp=100,
                    reputation=50,
                    quest_id="test-quest-456"
                )
    
    @pytest.mark.asyncio
    async def test_track_failed_reward_complete_flow(self, db_client):
        """Test the complete track_failed_reward flow"""
        db_client.failed_rewards_table_name = "test-failed-rewards"
        
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.put_item = AsyncMock(return_value={'ResponseMetadata': {'HTTPStatusCode': 200}})
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            await db_client.track_failed_reward(
                user_id="user-123",
                quest_id="quest-789",
                xp=50,
                reputation=25,
                error="Test error"
            )
            
            # Verify the put_item call
            mock_dynamodb_client.put_item.assert_called_once()
            call_args = mock_dynamodb_client.put_item.call_args[1]
            
            assert call_args['Item']['error']['S'] == "Test error"
            assert call_args['Item']['retryCount']['N'] == "0"


class TestFailedRewardRecovery:
    """Test the failed reward recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_get_pending_failed_rewards(self, db_client):
        """Test retrieving pending failed rewards"""
        db_client.failed_rewards_table_name = "test-failed-rewards"
        
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.scan.return_value = {
            'Items': [
                {
                    'rewardId': {'S': 'failure-1'},
                    'userId': {'S': 'user-1'},
                    'questId': {'S': 'quest-1'},
                    'xpAmount': {'N': '100'},
                    'reputationAmount': {'N': '50'},
                    'questPointsAmount': {'N': '0'},
                    'errorMessage': {'S': 'Test error'},
                    'retryCount': {'N': '0'},
                    'status': {'S': 'pending'},
                    'createdAt': {'S': '2025-01-01T00:00:00Z'},
                    'updatedAt': {'S': '2025-01-01T00:00:00Z'}
                },
                {
                    'rewardId': {'S': 'failure-2'},
                    'userId': {'S': 'user-2'},
                    'questId': {'S': 'quest-2'},
                    'xpAmount': {'N': '200'},
                    'reputationAmount': {'N': '100'},
                    'questPointsAmount': {'N': '0'},
                    'errorMessage': {'S': 'Another error'},
                    'retryCount': {'N': '1'},
                    'status': {'S': 'pending'},
                    'createdAt': {'S': '2025-01-01T00:00:00Z'},
                    'updatedAt': {'S': '2025-01-01T00:00:00Z'}
                }
            ]
        }
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            failures = await db_client.get_pending_failed_rewards()
            
            assert len(failures) == 2
            assert failures[0].userId == 'user-1'
            assert failures[0].xpAmount == 100
            assert failures[1].userId == 'user-2'
            assert failures[1].reputationAmount == 100
    
    @pytest.mark.asyncio
    async def test_mark_reward_completed(self, db_client):
        """Test marking a failed reward as completed"""
        db_client.failed_rewards_table_name = "test-failed-rewards"
        
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item = AsyncMock(return_value={'Attributes': {}})
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            await db_client.mark_reward_completed("failure-123")
            
            # Verify the update call
            mock_dynamodb_client.update_item.assert_called_once()
            call_args = mock_dynamodb_client.update_item.call_args[1]
            
            assert call_args['Key']['recordId']['S'] == "failure-123"
            assert ':status' in call_args['ExpressionAttributeValues']
            assert call_args['ExpressionAttributeValues'][':status']['S'] == 'completed'


class TestDatabaseConnectionErrors:
    """Test handling of database connection and resource errors"""
    
    @pytest.mark.asyncio
    async def test_get_user_handles_connection_error(self, db_client):
        """Test get_user handles connection errors gracefully"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.get_item.side_effect = ClientError(
            {'Error': {'Code': 'RequestLimitExceeded'}},
            'GetItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.get_user("user-123")
            assert result is None  # Should return None on error
    
    @pytest.mark.asyncio
    async def test_get_quest_handles_throttling(self, db_client):
        """Test get_quest handles throttling errors"""
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException'}},
            'GetItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.get_quest("quest-123")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_create_quest_propagates_errors(self, db_client):
        """Test create_quest propagates critical errors"""
        quest = Quest(
            questId="quest-123",
            creatorId="creator-123",
            title="Test Quest",
            description="Test",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException'}},
            'PutItem'
        )
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            with pytest.raises(ClientError):
                await db_client.create_quest(quest)


class TestQueryOperationErrors:
    """Test error handling in query operations"""
    
    @pytest.mark.asyncio
    async def test_list_quests_gsi_not_found_fallback(self, db_client):
        """Test list_quests falls back to scan when GSI doesn't exist"""
        mock_dynamodb_client = AsyncMock()
        
        # Query fails with GSI not found
        mock_dynamodb_client.query.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'GSI not found'}},
            'Query'
        )
        
        # Scan should work
        mock_dynamodb_client.scan.return_value = {
            'Items': [
                db_client._serialize_item({
                    'questId': 'quest-1',
                    'status': 'OPEN',
                    'title': 'Test Quest',
                    'description': 'Test description',
                    'creatorId': 'user-123',
                    'createdAt': '2025-01-01T00:00:00Z',
                    'updatedAt': '2025-01-01T00:00:00Z',
                    'rewardXp': 100,
                    'rewardReputation': 10,
                    'attestations': []
                })
            ]
        }
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            quests = await db_client.list_quests(status=QuestStatus.OPEN)
            
            # Should have called scan after query failed
            mock_dynamodb_client.scan.assert_called()
            assert len(quests) == 1
    
    @pytest.mark.asyncio
    async def test_get_user_stats_handles_errors(self, db_client):
        """Test get_user_stats handles query errors"""
        mock_dynamodb_client = AsyncMock()
        
        # First query fails
        mock_dynamodb_client.query.side_effect = [
            ClientError({'Error': {'Code': 'InternalServerError'}}, 'Query'),
            {'Count': 5}  # Second query succeeds
        ]
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should handle partial failure
            stats = await db_client.get_user_stats("user-123")
            
            # Should have default values for failed query
            assert stats is not None
            assert 'questsCreated' in stats
            assert stats['questsCreated'] == 0  # Failed query defaults to 0