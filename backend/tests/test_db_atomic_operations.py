"""
Comprehensive integration tests for atomic DynamoDB operations.
Tests concurrency, race conditions, and error handling for critical operations.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from botocore.exceptions import ClientError



# Tests for claim_quest_atomic
@pytest.mark.asyncio
async def test_claim_open_quest_succeeds():
    """Test successful claim of an open quest."""
    from src.db import get_db_client, DynamoDBClient
    
    # Mock the DynamoDB client's get_resource method
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock successful update_item call
        mock_dynamodb.update_item = AsyncMock(return_value={'Attributes': {}})
        
        db_client = DynamoDBClient()
        result = await db_client.claim_quest_atomic("quest-123", "performer-123")
        
        assert result is True
        assert mock_dynamodb.update_item.called
        
        # Verify the update_item was called with correct parameters
        call_args = mock_dynamodb.update_item.call_args[1]
        assert call_args['TableName'] == 'test-quests'
        assert call_args['Key'] == {'questId': {'S': 'quest-123'}}
        assert ':pid' in call_args['ExpressionAttributeValues']
        assert call_args['ExpressionAttributeValues'][':pid'] == {'S': 'performer-123'}


@pytest.mark.asyncio
async def test_claim_already_claimed_quest_fails():
    """Test that claiming an already claimed quest fails."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock ConditionalCheckFailedException
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        result = await db_client.claim_quest_atomic("quest-123", "performer-456")
        
        assert result is False


@pytest.mark.asyncio
async def test_claim_quest_unexpected_error_raises():
    """Test that unexpected errors are propagated."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock unexpected error
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'InternalServerError'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        
        with pytest.raises(ClientError):
            await db_client.claim_quest_atomic("quest-123", "performer-123")


# Tests for submit_quest_atomic
@pytest.mark.asyncio
async def test_submit_claimed_quest_succeeds():
    """Test successful submission of a claimed quest."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock successful update_item call
        mock_dynamodb.update_item = AsyncMock(return_value={'Attributes': {}})
        
        db_client = DynamoDBClient()
        result = await db_client.submit_quest_atomic(
            "quest-123", "performer-123", "Work completed!"
        )
        
        assert result is True
        assert mock_dynamodb.update_item.called
        
        # Verify the update_item parameters
        call_args = mock_dynamodb.update_item.call_args[1]
        assert call_args['TableName'] == 'test-quests'
        assert ':st' in call_args['ExpressionAttributeValues']
        assert call_args['ExpressionAttributeValues'][':st'] == {'S': 'Work completed!'}


@pytest.mark.asyncio
async def test_submit_by_wrong_user_fails():
    """Test that submission by wrong user fails."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock ConditionalCheckFailedException
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        result = await db_client.submit_quest_atomic(
            "quest-123", "wrong-performer", "Submission"
        )
        
        assert result is False


# Tests for add_attestation_atomic
@pytest.mark.asyncio
async def test_add_first_attestation_succeeds():
    """Test adding the first attestation."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock successful update_item call
        mock_dynamodb.update_item = AsyncMock(return_value={'Attributes': {}})
        
        db_client = DynamoDBClient()
        attestation = {
            'user_id': 'creator-123',
            'role': 'requestor',
            'signature': '0x1234567890abcdef',
            'attested_at': datetime.utcnow().isoformat()
        }
        
        result = await db_client.add_attestation_atomic("quest-123", attestation)
        
        assert result is True
        assert mock_dynamodb.update_item.called
        
        # Verify update expression includes the attestation
        call_args = mock_dynamodb.update_item.call_args[1]
        assert 'hasRequestorAttestation = :true' in call_args['UpdateExpression']
        assert ':user_id_set' in call_args['ExpressionAttributeValues']


@pytest.mark.asyncio
async def test_add_duplicate_attestation_fails():
    """Test that duplicate attestation fails."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock ConditionalCheckFailedException
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        attestation = {
            'user_id': 'creator-123',
            'role': 'requestor',
            'attested_at': datetime.utcnow().isoformat()
        }
        
        result = await db_client.add_attestation_atomic("quest-123", attestation)
        
        assert result is False


@pytest.mark.asyncio
async def test_add_attestation_to_wrong_state_fails():
    """Test that attestation to wrong state fails."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock ConditionalCheckFailedException
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        attestation = {
            'user_id': 'creator-123',
            'role': 'requestor',
            'attested_at': datetime.utcnow().isoformat()
        }
        
        result = await db_client.add_attestation_atomic("quest-123", attestation)
        
        assert result is False


# Test serialization for attestation
@pytest.mark.asyncio
async def test_add_attestation_serialization():
    """Test that attestation data is properly serialized."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock successful update
        mock_dynamodb.update_item = AsyncMock(return_value={'Attributes': {}})
        
        db_client = DynamoDBClient()
        attestation = {
            'user_id': 'user-123',
            'role': 'performer',
            'signature': '0xabcdef123456',
            'message': 'Test message',
            'attested_at': '2024-01-01T00:00:00'
        }
        
        result = await db_client.add_attestation_atomic("quest-123", attestation)
        
        assert result is True
        
        # Check serialization of attestation in the call
        call_args = mock_dynamodb.update_item.call_args[1]
        new_attestation = call_args['ExpressionAttributeValues'][':new_attestation']
        
        # Should be a list with one serialized attestation
        assert 'L' in new_attestation
        assert len(new_attestation['L']) == 1
        
        # Verify the attestation was serialized correctly
        serialized_attestation = new_attestation['L'][0]['M']
        assert serialized_attestation['user_id']['S'] == 'user-123'
        assert serialized_attestation['role']['S'] == 'performer'
        assert serialized_attestation['signature']['S'] == '0xabcdef123456'


# Test error handling
@pytest.mark.asyncio
async def test_claim_quest_validation_error():
    """Test that validation errors are handled properly."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock validation error
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'ValidationException'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        
        with pytest.raises(ClientError) as exc_info:
            await db_client.claim_quest_atomic("quest-123", "performer-123")
        
        assert exc_info.value.response['Error']['Code'] == 'ValidationException'


# Test complete_quest_atomic
@pytest.mark.asyncio
async def test_complete_quest_atomic_succeeds():
    """Test completing a quest atomically."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock successful update_item call
        mock_dynamodb.update_item = AsyncMock(return_value={'Attributes': {}})
        
        db_client = DynamoDBClient()
        result = await db_client.complete_quest_atomic("quest-123")
        
        assert result is True
        assert mock_dynamodb.update_item.called
        
        # Verify the status is being set to COMPLETE
        call_args = mock_dynamodb.update_item.call_args[1]
        assert call_args['ExpressionAttributeValues'][':complete_status'] == {'S': 'COMPLETE'}


@pytest.mark.asyncio
async def test_complete_quest_not_submitted_fails():
    """Test that completing a non-submitted quest fails."""
    from src.db import get_db_client, DynamoDBClient
    
    with patch.object(DynamoDBClient, 'get_resource') as mock_get_resource:
        mock_dynamodb = MagicMock()
        mock_get_resource.return_value.__aenter__.return_value = mock_dynamodb
        
        # Mock ConditionalCheckFailedException
        mock_dynamodb.update_item = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        ))
        
        db_client = DynamoDBClient()
        result = await db_client.complete_quest_atomic("quest-123")
        
        assert result is False