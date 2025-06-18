"""Failed reward repository for centralized failed reward tracking with distributed locking."""
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from .base import BaseRepository


class FailedRewardRepository(BaseRepository):
    """Centralized data access for failed rewards with distributed locking."""
    
    def __init__(self):
        """Initialize failed reward repository."""
        table_name = os.environ.get('FAILED_REWARDS_TABLE', 'civicforge-failed-rewards')
        super().__init__(table_name)
        self.lease_duration_seconds = 300  # 5 minutes
    
    async def track_failed_reward(
        self,
        user_id: str,
        quest_id: str,
        xp: int,
        reputation: int,
        error: str
    ) -> str:
        """Track a failed reward for later processing."""
        try:
            record_id = str(uuid.uuid4())
            
            self.table.put_item(
                Item={
                    'recordId': record_id,
                    'userId': user_id,
                    'questId': quest_id,
                    'xp': Decimal(str(xp)),
                    'reputation': Decimal(str(reputation)),
                    'error': error,
                    'status': 'pending',
                    'createdAt': datetime.utcnow().isoformat(),
                    'retryCount': 0
                }
            )
            
            self.logger.info(
                "failed_reward_tracked",
                record_id=record_id,
                user_id=user_id,
                quest_id=quest_id
            )
            return record_id
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "track_failed_reward")
            raise
    
    async def get_pending_rewards(
        self,
        limit: int = 10,
        start_key: Optional[Dict] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict]]:
        """Get pending failed rewards using GSI."""
        try:
            query_params = {
                'IndexName': 'status-createdAt-index',
                'KeyConditionExpression': Key('status').eq('pending'),
                'Limit': limit
            }
            
            if start_key:
                query_params['ExclusiveStartKey'] = start_key
            
            response = self.table.query(**query_params)
            
            rewards = response.get('Items', [])
            next_key = response.get('LastEvaluatedKey')
            
            return rewards, next_key
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "get_pending_rewards")
            return [], None
    
    async def acquire_processing_lease(self, record_id: str, owner_id: str) -> bool:
        """Acquire distributed lock for processing a reward."""
        try:
            now = datetime.utcnow()
            expiry = now + timedelta(seconds=self.lease_duration_seconds)
            
            self.table.update_item(
                Key={'recordId': record_id},
                UpdateExpression='SET leaseOwner = :owner, leaseExpiresAt = :expiry',
                ConditionExpression='attribute_not_exists(leaseOwner) OR leaseExpiresAt < :now',
                ExpressionAttributeValues={
                    ':owner': owner_id,
                    ':expiry': expiry.isoformat(),
                    ':now': now.isoformat()
                }
            )
            
            self.logger.info(
                "lease_acquired",
                record_id=record_id,
                owner_id=owner_id,
                expires_at=expiry.isoformat()
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.debug(
                    "lease_already_held",
                    record_id=record_id
                )
                return False
            
            await self._handle_dynamodb_error(e, "acquire_processing_lease")
            return False
    
    async def release_lease(self, record_id: str, owner_id: str) -> bool:
        """Release processing lease."""
        try:
            self.table.update_item(
                Key={'recordId': record_id},
                UpdateExpression='REMOVE leaseOwner, leaseExpiresAt',
                ConditionExpression='leaseOwner = :owner',
                ExpressionAttributeValues={
                    ':owner': owner_id
                }
            )
            
            self.logger.info(
                "lease_released",
                record_id=record_id,
                owner_id=owner_id
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "lease_not_owned",
                    record_id=record_id,
                    owner_id=owner_id
                )
                return False
            
            await self._handle_dynamodb_error(e, "release_lease")
            return False
    
    async def mark_completed(self, record_id: str) -> bool:
        """Mark failed reward as completed."""
        try:
            self.table.update_item(
                Key={'recordId': record_id},
                UpdateExpression='SET #s = :status, completedAt = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "reward_marked_completed",
                record_id=record_id
            )
            return True
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "mark_completed")
            return False
    
    async def update_status(
        self,
        record_id: str,
        status: str,
        error: Optional[str] = None,
        increment_retry: bool = False
    ) -> bool:
        """Update reward status with optional retry increment."""
        try:
            update_parts = ['#s = :status']
            expr_names = {'#s': 'status'}
            expr_values = {
                ':status': status,
                ':now': datetime.utcnow().isoformat()
            }
            
            if error:
                update_parts.append('error = :error')
                expr_values[':error'] = error
            
            if increment_retry:
                update_parts.append('retryCount = retryCount + :inc')
                expr_values[':inc'] = 1
            
            if status == 'failed':
                update_parts.append('failedAt = :now')
            elif status == 'completed':
                update_parts.append('completedAt = :now')
            
            update_expr = f"SET {', '.join(update_parts)}"
            
            self.table.update_item(
                Key={'recordId': record_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
            
            self.logger.info(
                "reward_status_updated",
                record_id=record_id,
                status=status,
                increment_retry=increment_retry
            )
            return True
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "update_status")
            return False
    
    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get failed reward by ID."""
        try:
            response = self.table.get_item(Key={'recordId': record_id})
            
            if 'Item' not in response:
                return None
            
            return response['Item']
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "get_failed_reward")
            return None