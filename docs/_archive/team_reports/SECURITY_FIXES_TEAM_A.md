# Team A: Security Fixes Implementation Guide

## Overview

This document outlines the critical security fixes required before MVP deployment, focusing on IAM permission hardening and test coverage for critical components.

## Priority 1: Fix attestQuest Lambda IAM Permissions

### Current Issue
The `attestQuest` Lambda has overly permissive `dynamodb:UpdateItem` access to the entire users table, allowing potential modification of any user attribute.

### Implementation

1. **Update serverless.yml for attestQuest handler**

Replace the current IAM role statement for the users table with:

```yaml
attestQuest:
  handler: handlers.attest_quest.handler
  events:
    - httpApi:
        path: /api/v1/quests/{quest_id}/attest
        method: POST
  iamRoleStatements:
    # ... (keep existing quest table permissions)
    - Effect: Allow
      Action:
        - dynamodb:UpdateItem
      Resource:
        - "arn:aws:dynamodb:${self:provider.region}:${aws:accountId}:table/${self:custom.usersTable}"
      Condition:
        ForAllValues:StringEquals:
          dynamodb:Attributes:
            - reputation
            - experience
            - questCreationPoints
            - processedRewardIds
            - updatedAt
```

This ensures the Lambda can only update reward-related attributes, not sensitive fields like `walletAddress` or `email`.

## Priority 2: Create Isolated Wallet Update Lambda

### Implementation Steps

1. **Create new handler file: `backend/handlers/update_wallet.py`**

```python
"""
Isolated handler for wallet address updates with strict IAM permissions
"""
import json
import logging
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from src.auth import get_current_user_id
from src.db import get_db_client

logger = Logger()

async def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Update user's wallet address with strict permission controls
    """
    try:
        # Get authenticated user ID
        user_id = await get_current_user_id(event)
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        wallet_address = body.get('walletAddress')
        
        if not wallet_address:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'walletAddress is required'})
            }
        
        # Update only the wallet address
        db = get_db_client()
        await db.update_user_wallet(user_id, wallet_address)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Wallet address updated successfully'})
        }
        
    except Exception as e:
        logger.error(f"Failed to update wallet address: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

2. **Add to serverless.yml with restricted permissions**

```yaml
updateWallet:
  handler: handlers.update_wallet.handler
  events:
    - httpApi:
        path: /api/v1/users/wallet
        method: PUT
  iamRoleStatements:
    - Effect: Allow
      Action:
        - dynamodb:UpdateItem
      Resource:
        - "arn:aws:dynamodb:${self:provider.region}:${aws:accountId}:table/${self:custom.usersTable}"
      Condition:
        ForAllValues:StringEquals:
          dynamodb:Attributes:
            - walletAddress
            - updatedAt
```

3. **Remove wallet update permissions from main API handler**

Update the `api` handler in serverless.yml to remove UpdateItem permission on the users table.

## Priority 3: Fix Attestation Logic Bug

### Current Issue
The attestation logic in `db.py:600` doesn't properly prevent duplicate attestations from different users with the same role.

### Implementation

Update `backend/src/db.py` in the `add_attestation_atomic` method:

```python
async def add_attestation_atomic(self, quest_id: str, attestation: Dict[str, Any], user_id: str) -> bool:
    """Add attestation atomically with proper duplicate prevention"""
    
    # Determine the condition field based on attestation role
    is_requestor = attestation.get('role') == 'REQUESTOR'
    condition_field = 'hasRequestorAttestation' if is_requestor else 'hasPerformerAttestation'
    
    try:
        dynamodb = await self.get_resource()
        
        # Update the condition expression to check attesterIds set membership
        response = await dynamodb.update_item(
            TableName=self.quests_table_name,
            Key={'questId': {'S': quest_id}},
            UpdateExpression=f"""
                SET attestations = list_append(if_not_exists(attestations, :empty_list), :new_attestation),
                    {condition_field} = :true,
                    updatedAt = :now
                ADD attesterIds :user_id_set
            """,
            ConditionExpression="""
                attribute_exists(questId) AND 
                #status = :submitted_status AND 
                NOT contains(attesterIds, :user_id)
            """,
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':new_attestation': {'L': [self._serialize_item(attestation)]},
                ':user_id': {'S': user_id},
                ':user_id_set': {'SS': [user_id]},
                ':true': {'BOOL': True},
                ':submitted_status': {'S': 'SUBMITTED'},
                ':now': {'S': datetime.utcnow().isoformat()},
                ':empty_list': {'L': []}
            }
        )
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.warning(f"User {user_id} already attested to quest {quest_id}")
            return False
        raise
```

## Priority 4: Create Tests for reprocess_failed_rewards

### Implementation

Create `backend/tests/triggers/test_reprocess_failed_rewards.py`:

```python
"""
Comprehensive tests for the failed rewards reprocessor
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
from moto import mock_dynamodb
import boto3
from botocore.exceptions import ClientError

from src.triggers.reprocess_failed_rewards import (
    handler, acquire_lease, release_lease, process_reward_with_lease,
    is_reward_already_processed, award_rewards_idempotently
)

@pytest.fixture
def mock_tables():
    """Set up mock DynamoDB tables"""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create users table
        users_table = dynamodb.create_table(
            TableName='test-users',
            KeySchema=[{'AttributeName': 'userId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'userId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create failed rewards table
        failed_rewards_table = dynamodb.create_table(
            TableName='test-failed-rewards',
            KeySchema=[{'AttributeName': 'rewardId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'rewardId', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'createdAt', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'status-createdAt-index',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'},
                    {'AttributeName': 'createdAt', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield {
            'users_table': users_table,
            'failed_rewards_table': failed_rewards_table
        }

class TestLeaseManagement:
    """Test lease acquisition and release"""
    
    def test_acquire_lease_success(self, mock_tables):
        """Test successful lease acquisition"""
        table = mock_tables['failed_rewards_table']
        reward_id = 'test-reward-1'
        
        # Add a reward without lease
        table.put_item(Item={
            'rewardId': reward_id,
            'status': 'pending'
        })
        
        # Acquire lease
        current_time = datetime.now(timezone.utc)
        assert acquire_lease(reward_id, current_time) is True
        
        # Verify lease was set
        response = table.get_item(Key={'rewardId': reward_id})
        assert 'leaseOwner' in response['Item']
        assert 'leaseExpiresAt' in response['Item']
    
    def test_acquire_lease_already_taken(self, mock_tables):
        """Test lease acquisition when already taken"""
        table = mock_tables['failed_rewards_table']
        reward_id = 'test-reward-2'
        current_time = datetime.now(timezone.utc)
        future_time = current_time + timedelta(minutes=10)
        
        # Add a reward with active lease
        table.put_item(Item={
            'rewardId': reward_id,
            'status': 'pending',
            'leaseOwner': 'other-worker',
            'leaseExpiresAt': future_time.isoformat()
        })
        
        # Try to acquire lease
        assert acquire_lease(reward_id, current_time) is False
    
    def test_acquire_lease_expired(self, mock_tables):
        """Test acquiring an expired lease"""
        table = mock_tables['failed_rewards_table']
        reward_id = 'test-reward-3'
        current_time = datetime.now(timezone.utc)
        past_time = current_time - timedelta(minutes=10)
        
        # Add a reward with expired lease
        table.put_item(Item={
            'rewardId': reward_id,
            'status': 'pending',
            'leaseOwner': 'old-worker',
            'leaseExpiresAt': past_time.isoformat()
        })
        
        # Should be able to acquire expired lease
        assert acquire_lease(reward_id, current_time) is True

class TestIdempotency:
    """Test idempotent reward processing"""
    
    def test_reward_already_processed(self, mock_tables):
        """Test detection of already processed rewards"""
        users_table = mock_tables['users_table']
        user_id = 'test-user-1'
        reward_id = 'test-reward-1'
        
        # Add user with processed reward
        users_table.put_item(Item={
            'userId': user_id,
            'processedRewardIds': {reward_id}
        })
        
        # Check if already processed
        assert is_reward_already_processed(user_id, reward_id) is True
        assert is_reward_already_processed(user_id, 'other-reward') is False
    
    def test_award_rewards_idempotently_success(self, mock_tables):
        """Test successful reward awarding"""
        users_table = mock_tables['users_table']
        user_id = 'test-user-2'
        reward_id = 'test-reward-2'
        
        # Add user without reward
        users_table.put_item(Item={
            'userId': user_id,
            'xp': 100,
            'reputation': 50,
            'questPoints': 10
        })
        
        # Award rewards
        result = award_rewards_idempotently(
            user_id=user_id,
            reward_id=reward_id,
            xp_amount=20,
            reputation_amount=10,
            quest_points_amount=5
        )
        
        assert result is True
        
        # Verify rewards were applied
        response = users_table.get_item(Key={'userId': user_id})
        user = response['Item']
        assert user['xp'] == 120
        assert user['reputation'] == 60
        assert user['questPoints'] == 15
        assert reward_id in user['processedRewardIds']
    
    def test_award_rewards_idempotently_duplicate(self, mock_tables):
        """Test duplicate reward prevention"""
        users_table = mock_tables['users_table']
        user_id = 'test-user-3'
        reward_id = 'test-reward-3'
        
        # Add user with already processed reward
        users_table.put_item(Item={
            'userId': user_id,
            'xp': 100,
            'processedRewardIds': [reward_id]
        })
        
        # Try to award same reward again
        result = award_rewards_idempotently(
            user_id=user_id,
            reward_id=reward_id,
            xp_amount=20,
            reputation_amount=10,
            quest_points_amount=5
        )
        
        # Should return True (idempotent) but not double-award
        assert result is True
        
        # Verify no double rewards
        response = users_table.get_item(Key={'userId': user_id})
        assert response['Item']['xp'] == 100  # Unchanged

class TestRetryLogic:
    """Test retry and abandonment logic"""
    
    @patch('src.triggers.reprocess_failed_rewards.MAX_RETRY_ATTEMPTS', 3)
    def test_max_retries_abandonment(self, mock_tables):
        """Test reward abandonment after max retries"""
        failed_table = mock_tables['failed_rewards_table']
        reward_id = 'test-reward-retry'
        
        item = {
            'rewardId': reward_id,
            'userId': 'test-user',
            'retryCount': 3,  # Already at max
            'status': 'pending'
        }
        
        with patch('src.triggers.reprocess_failed_rewards.update_reward_status') as mock_update:
            result = process_reward_with_lease(item, datetime.now(timezone.utc))
            assert result == 'abandoned'
            mock_update.assert_called_with(reward_id, 'abandoned', 3)

class TestHandlerIntegration:
    """Test the main handler function"""
    
    @patch.dict('os.environ', {
        'USERS_TABLE': 'test-users',
        'FAILED_REWARDS_TABLE': 'test-failed-rewards',
        'MAX_RETRY_ATTEMPTS': '5',
        'LEASE_DURATION_SECONDS': '300'
    })
    def test_handler_success(self, mock_tables):
        """Test successful handler execution"""
        failed_table = mock_tables['failed_rewards_table']
        users_table = mock_tables['users_table']
        
        # Add pending rewards
        for i in range(3):
            failed_table.put_item(Item={
                'rewardId': f'reward-{i}',
                'userId': f'user-{i}',
                'status': 'pending',
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'xpAmount': 10,
                'reputationAmount': 5
            })
            
            # Add corresponding users
            users_table.put_item(Item={
                'userId': f'user-{i}',
                'xp': 0,
                'reputation': 0
            })
        
        # Run handler
        result = handler({}, None)
        
        assert result['processed'] >= 3
        assert result['succeeded'] >= 0
        assert 'timestamp' in result

# Additional edge case tests...
```

## Priority 5: Security Audit Tests

Create test file to verify IAM restrictions work as expected:

```python
"""
Security audit tests for IAM permission restrictions
"""
import pytest
from unittest.mock import patch, MagicMock
import boto3
from botocore.exceptions import ClientError

class TestIAMRestrictions:
    """Verify IAM restrictions are properly enforced"""
    
    @patch('boto3.client')
    def test_attest_quest_cannot_update_wallet(self, mock_boto):
        """Verify attestQuest Lambda cannot update wallet address"""
        mock_dynamodb = MagicMock()
        mock_boto.return_value = mock_dynamodb
        
        # Simulate IAM denial for wallet update
        mock_dynamodb.update_item.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 
                      'Message': 'User is not authorized to perform: dynamodb:UpdateItem on attribute: walletAddress'}},
            'UpdateItem'
        )
        
        # Try to update wallet (should fail)
        with pytest.raises(ClientError) as exc_info:
            mock_dynamodb.update_item(
                TableName='users',
                Key={'userId': {'S': 'test-user'}},
                UpdateExpression='SET walletAddress = :addr',
                ExpressionAttributeValues={':addr': {'S': '0x123'}}
            )
        
        assert exc_info.value.response['Error']['Code'] == 'AccessDeniedException'
    
    def test_wallet_lambda_cannot_update_reputation(self):
        """Verify wallet update Lambda cannot modify reputation"""
        # Similar test for wallet Lambda restrictions
        pass
```

## Testing Checklist

- [ ] All IAM permission changes tested in staging environment
- [ ] Condition keys verified to work as expected
- [ ] Failed rewards reprocessor has 100% test coverage
- [ ] Integration tests pass with new IAM restrictions
- [ ] API contract documented for frontend team

## Rollback Plan

If any issues arise:

1. Revert serverless.yml to previous IAM configuration
2. Deploy rollback with `serverless deploy --stage staging`
3. Verify services are operational
4. Investigate and fix issues before re-attempting

## Success Criteria

- Zero security vulnerabilities in IAM permissions
- All Lambda functions follow principle of least privilege
- 100% test coverage for rewards reprocessor
- All tests passing in CI/CD pipeline