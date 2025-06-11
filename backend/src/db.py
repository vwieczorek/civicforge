"""
DynamoDB client for quest and user operations
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import aiobotocore
from aiobotocore.session import get_session
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .models import Quest, QuestDB, User, FailedReward, QuestStatus

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DynamoDBClient:
    """Minimal DynamoDB operations for dual-attestation"""
    
    def __init__(self):
        self.users_table_name = os.environ.get("USERS_TABLE", "civicforge-users")
        self.quests_table_name = os.environ.get("QUESTS_TABLE", "civicforge-quests")
        self.failed_rewards_table_name = os.environ.get('FAILED_REWARDS_TABLE')
        self._session = get_session()
        self._client = None
    
    @asynccontextmanager
    async def get_resource(self):
        """Get async DynamoDB client with lifecycle management"""
        if self._client is None:
            # Support endpoint_url for testing
            endpoint_url = os.environ.get('DYNAMODB_ENDPOINT_URL')
            kwargs = {}
            if endpoint_url:
                kwargs['endpoint_url'] = endpoint_url
            self._client = await self._session.create_client('dynamodb', **kwargs).__aenter__()
        
        yield self._client
    
    async def close(self):
        """Close the DynamoDB client"""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            async with self.get_resource() as dynamodb:
                logger.info(f"Getting user {user_id} from table {self.users_table_name}")
                response = await dynamodb.get_item(
                    TableName=self.users_table_name,
                    Key={'userId': {'S': user_id}}
                )
            if 'Item' in response:
                # Convert DynamoDB format to dict
                item = self._deserialize_item(response['Item'])
                return User(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get quest by ID"""
        try:
            async with self.get_resource() as dynamodb:
                response = await dynamodb.get_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}}
                )
            if 'Item' in response:
                item = self._deserialize_item(response['Item'])
                return Quest(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting quest {quest_id}: {e}")
            return None
    
    async def create_user(self, user: User) -> None:
        """Create new user"""
        try:
            user_dict = user.model_dump()
            user_dict['createdAt'] = datetime.utcnow().isoformat()
            user_dict['updatedAt'] = user_dict['createdAt']
            
            async with self.get_resource() as dynamodb:
                await dynamodb.put_item(
                    TableName=self.users_table_name,
                    Item=self._serialize_item(user_dict)
                )
        except ClientError as e:
            logger.error(f"Error creating user {user.userId}: {e}")
            raise
    
    async def update_quest(self, quest: Quest) -> None:
        """Update quest in database"""
        try:
            quest_dict = quest.model_dump()
            
            # Convert datetime objects to ISO strings
            for key, value in quest_dict.items():
                if isinstance(value, datetime):
                    quest_dict[key] = value.isoformat()
                elif key == 'attestations' and value:
                    # Ensure attestations have proper datetime format
                    for attestation in value:
                        if 'timestamp' in attestation and isinstance(attestation['timestamp'], datetime):
                            attestation['timestamp'] = attestation['timestamp'].isoformat()
            
            quest_dict['updatedAt'] = datetime.utcnow().isoformat()
            
            async with self.get_resource() as dynamodb:
                await dynamodb.put_item(
                    TableName=self.quests_table_name,
                    Item=self._serialize_item(quest_dict)
                )
            
        except ClientError as e:
            logger.error(f"Error updating quest {quest.questId}: {e}")
            raise
    
    async def create_quest(self, quest: Quest) -> None:
        """Create new quest"""
        try:
            quest_dict = quest.model_dump()
            quest_dict['createdAt'] = datetime.utcnow().isoformat()
            quest_dict['updatedAt'] = quest_dict['createdAt']
            
            async with self.get_resource() as dynamodb:
                await dynamodb.put_item(
                    TableName=self.quests_table_name,
                    Item=self._serialize_item(quest_dict)
                )
        except ClientError as e:
            logger.error(f"Error creating quest {quest.questId}: {e}")
            raise
    
    async def get_quest_for_update(self, quest_id: str) -> Optional[Quest]:
        """Get quest for update with strong consistency"""
        try:
            async with self.get_resource() as dynamodb:
                response = await dynamodb.get_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    ConsistentRead=True
                )
            if 'Item' in response:
                item = self._deserialize_item(response['Item'])
                return Quest(**item)
            return None
        except ClientError as e:
            logger.error(f"Error getting quest {quest_id} for update: {e}")
            return None
    
    async def award_rewards(
        self, 
        user_id: str, 
        xp: int, 
        reputation: int,
        quest_id: str = None
    ) -> None:
        """Award XP and reputation to user"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.users_table_name,
                    Key={'userId': {'S': user_id}},
                    UpdateExpression="ADD experience :xp, reputation :rep SET updatedAt = :now",
                    ExpressionAttributeValues={
                        ':xp': {'N': str(xp)},
                        ':rep': {'N': str(reputation)},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except ClientError as e:
            logger.error(f"Error awarding rewards to user {user_id}: {e}")
            # Track failed reward if table is configured
            if self.failed_rewards_table_name and quest_id:
                await self.track_failed_reward(user_id, quest_id, xp, reputation, str(e))
            raise
    
    async def deduct_quest_creation_points(self, user_id: str) -> bool:
        """Deduct points for quest creation"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.users_table_name,
                    Key={'userId': {'S': user_id}},
                    UpdateExpression="SET questCreationPoints = questCreationPoints - :points, updatedAt = :now",
                    ConditionExpression="questCreationPoints >= :points",
                    ExpressionAttributeValues={
                        ':points': {'N': '1'},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            logger.error(f"Error deducting quest creation points: {e}")
            raise
    
    async def get_pending_failed_rewards(self) -> List[FailedReward]:
        """Get failed rewards that need retry"""
        if not self.failed_rewards_table_name:
            return []
            
        try:
            items = []
            last_evaluated_key = None
            
            async with self.get_resource() as dynamodb:
                while True:
                    params = {
                        'TableName': self.failed_rewards_table_name,
                        'FilterExpression': '#s = :status',
                        'ExpressionAttributeNames': {'#s': 'status'},
                        'ExpressionAttributeValues': {':status': {'S': 'pending'}}
                    }
                    
                    if last_evaluated_key:
                        params['ExclusiveStartKey'] = last_evaluated_key
                    
                    response = await dynamodb.scan(**params)
                    
                    items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                    
                    last_evaluated_key = response.get('LastEvaluatedKey')
                    if not last_evaluated_key:
                        break
                
                return [FailedReward(**item) for item in items]
                
        except ClientError as e:
            logger.error(f"Error getting failed rewards: {e}")
            return []
    
    async def mark_reward_completed(self, record_id: str) -> None:
        """Mark failed reward as completed"""
        if not self.failed_rewards_table_name:
            return
            
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.failed_rewards_table_name,
                    Key={'recordId': {'S': record_id}},
                    UpdateExpression="SET #s = :status, completedAt = :now",
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'completed'},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except ClientError as e:
            logger.error(f"Error marking reward completed: {e}")
    
    async def track_failed_reward(
        self, 
        user_id: str, 
        quest_id: str, 
        xp: int, 
        reputation: int, 
        error: str
    ) -> None:
        """Track failed reward for later retry"""
        if not self.failed_rewards_table_name:
            logger.warning("Failed rewards table not configured, cannot track failed reward")
            return
            
        try:
            record = {
                'recordId': str(uuid.uuid4()),
                'userId': user_id,
                'questId': quest_id,
                'xp': xp,
                'reputation': reputation,
                'error': error,
                'status': 'pending',
                'createdAt': datetime.utcnow().isoformat(),
                'retryCount': 0
            }
            
            async with self.get_resource() as dynamodb:
                await dynamodb.put_item(
                    TableName=self.failed_rewards_table_name,
                    Item=self._serialize_item(record)
                )
                
            logger.info(f"Tracked failed reward for user {user_id}, quest {quest_id}")
            
        except ClientError as e:
            logger.error(f"Error tracking failed reward: {e}")
    
    async def list_quests(self, status: Optional[str] = None) -> List[Quest]:
        """List all quests, optionally filtered by status"""
        try:
            items = []
            last_evaluated_key = None
            
            async with self.get_resource() as dynamodb:
                while True:
                    if status:
                        # Use GSI if available for better performance
                        params = {
                            'TableName': self.quests_table_name,
                            'IndexName': 'StatusIndex',
                            'KeyConditionExpression': '#s = :status',
                            'ExpressionAttributeNames': {'#s': 'status'},
                            'ExpressionAttributeValues': {':status': {'S': status}},
                            'ScanIndexForward': False
                        }
                        if last_evaluated_key:
                            params['ExclusiveStartKey'] = last_evaluated_key
                        
                        try:
                            response = await dynamodb.query(**params)
                        except ClientError as e:
                            if 'ResourceNotFoundException' in str(e):
                                # GSI doesn't exist, fall back to scan
                                logger.warning("StatusIndex GSI not found, falling back to scan")
                                return await self._list_quests_scan(status)
                            raise
                    else:
                        # Full scan when no status filter
                        params = {'TableName': self.quests_table_name}
                        if last_evaluated_key:
                            params['ExclusiveStartKey'] = last_evaluated_key
                        
                        response = await dynamodb.scan(**params)
                    
                    items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                    
                    last_evaluated_key = response.get('LastEvaluatedKey')
                    if not last_evaluated_key:
                        break
            
            quests = [Quest(**item) for item in items]
            
            # Sort by createdAt in descending order
            quests.sort(key=lambda q: q.createdAt, reverse=True)
            
            return quests
            
        except ClientError as e:
            logger.error(f"Error listing quests: {e}")
            raise
    
    async def _list_quests_scan(self, status: Optional[str] = None) -> List[Quest]:
        """Fallback scan method for listing quests"""
        try:
            items = []
            last_evaluated_key = None
            
            async with self.get_resource() as dynamodb:
                while True:
                    params = {'TableName': self.quests_table_name}
                    
                    if status:
                        params['FilterExpression'] = '#s = :status'
                        params['ExpressionAttributeNames'] = {'#s': 'status'}
                        params['ExpressionAttributeValues'] = {':status': {'S': status}}
                    
                    if last_evaluated_key:
                        params['ExclusiveStartKey'] = last_evaluated_key
                    
                    response = await dynamodb.scan(**params)
                    
                    items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                    
                    last_evaluated_key = response.get('LastEvaluatedKey')
                    if not last_evaluated_key:
                        break
            
            quests = [Quest(**item) for item in items]
            quests.sort(key=lambda q: q.createdAt, reverse=True)
            
            return quests
            
        except ClientError as e:
            logger.error(f"Error scanning quests: {e}")
            raise
    
    async def get_user_created_quests(self, user_id: str) -> List[Quest]:
        """Get quests created by a user"""
        try:
            items = []
            last_evaluated_key = None
            
            async with self.get_resource() as dynamodb:
                # Try to use GSI first
                try:
                    while True:
                        params = {
                            'TableName': self.quests_table_name,
                            'IndexName': 'CreatorIndex',
                            'KeyConditionExpression': 'creatorId = :uid',
                            'ExpressionAttributeValues': {':uid': {'S': user_id}},
                            'ScanIndexForward': False
                        }
                        if last_evaluated_key:
                            params['ExclusiveStartKey'] = last_evaluated_key
                        
                        response = await dynamodb.query(**params)
                        items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                        
                        last_evaluated_key = response.get('LastEvaluatedKey')
                        if not last_evaluated_key:
                            break
                            
                except ClientError as e:
                    if 'ResourceNotFoundException' in str(e):
                        # GSI doesn't exist, fall back to scan
                        logger.warning("CreatorIndex GSI not found, falling back to scan")
                        items = []
                        last_evaluated_key = None
                        
                        while True:
                            params = {
                                'TableName': self.quests_table_name,
                                'FilterExpression': 'creatorId = :uid',
                                'ExpressionAttributeValues': {':uid': {'S': user_id}}
                            }
                            if last_evaluated_key:
                                params['ExclusiveStartKey'] = last_evaluated_key
                            
                            response = await dynamodb.scan(**params)
                            items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                            
                            last_evaluated_key = response.get('LastEvaluatedKey')
                            if not last_evaluated_key:
                                break
                    else:
                        raise
            
            return [Quest(**item) for item in items]
            
        except ClientError as e:
            logger.error(f"Error getting user created quests: {e}")
            raise
    
    async def get_user_performed_quests(self, user_id: str) -> List[Quest]:
        """Get quests performed by a user"""
        try:
            items = []
            last_evaluated_key = None
            
            async with self.get_resource() as dynamodb:
                # Try to use GSI first
                try:
                    while True:
                        params = {
                            'TableName': self.quests_table_name,
                            'IndexName': 'PerformerIndex',
                            'KeyConditionExpression': 'performerId = :uid',
                            'ExpressionAttributeValues': {':uid': {'S': user_id}},
                            'ScanIndexForward': False
                        }
                        if last_evaluated_key:
                            params['ExclusiveStartKey'] = last_evaluated_key
                        
                        response = await dynamodb.query(**params)
                        items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                        
                        last_evaluated_key = response.get('LastEvaluatedKey')
                        if not last_evaluated_key:
                            break
                            
                except ClientError as e:
                    if 'ResourceNotFoundException' in str(e):
                        # GSI doesn't exist, fall back to scan
                        logger.warning("PerformerIndex GSI not found, falling back to scan")
                        items = []
                        last_evaluated_key = None
                        
                        while True:
                            params = {
                                'TableName': self.quests_table_name,
                                'FilterExpression': 'performerId = :uid',
                                'ExpressionAttributeValues': {':uid': {'S': user_id}}
                            }
                            if last_evaluated_key:
                                params['ExclusiveStartKey'] = last_evaluated_key
                            
                            response = await dynamodb.scan(**params)
                            items.extend([self._deserialize_item(item) for item in response.get('Items', [])])
                            
                            last_evaluated_key = response.get('LastEvaluatedKey')
                            if not last_evaluated_key:
                                break
                    else:
                        raise
            
            return [Quest(**item) for item in items]
            
        except ClientError as e:
            logger.error(f"Error getting user performed quests: {e}")
            raise
    
    async def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """Get user statistics"""
        try:
            # Get the user
            user = await self.get_user(user_id)
            if not user:
                return {
                    'questsCreated': 0,
                    'questsCompleted': 0,
                    'experience': 0,
                    'reputation': 0
                }
            
            # Get created quests count
            created_quests = await self.get_user_created_quests(user_id)
            
            # Get completed quests count
            performed_quests = await self.get_user_performed_quests(user_id)
            completed_count = sum(1 for q in performed_quests if q.status == QuestStatus.COMPLETE)
            
            return {
                'questsCreated': len(created_quests),
                'questsCompleted': completed_count,
                'experience': user.experience,
                'reputation': user.reputation
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                'questsCreated': 0,
                'questsCompleted': 0,
                'experience': 0,
                'reputation': 0
            }
    
    async def update_user_wallet(self, user_id: str, wallet_address: str) -> None:
        """Updates a user's wallet address"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.users_table_name,
                    Key={'userId': {'S': user_id}},
                    UpdateExpression="SET walletAddress = :addr, updatedAt = :now",
                    ExpressionAttributeValues={
                        ':addr': {'S': wallet_address},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except ClientError as e:
            logger.error(f"Error updating wallet for user {user_id}: {e}")
            raise
    
    async def award_quest_points(self, user_id: str, points: int) -> None:
        """Award points to a user, e.g., for quest creation refund"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.users_table_name,
                    Key={'userId': {'S': user_id}},
                    UpdateExpression="ADD questCreationPoints :points SET updatedAt = :now",
                    ExpressionAttributeValues={
                        ':points': {'N': str(points)},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except ClientError as e:
            logger.error(f"Error awarding quest points to user {user_id}: {e}")
            # For a refund, log but don't fail the operation
            pass
    
    async def add_attestation_atomic(
        self, 
        quest_id: str, 
        attestation: Dict[str, Any]
    ) -> bool:
        """Add attestation to quest atomically - prevents concurrent attestation issues"""
        try:
            async with self.get_resource() as dynamodb:
                # Determine which attestor role this is
                role = attestation.get('role')
                is_requestor = role == 'requestor'
                condition_field = 'hasRequestorAttestation' if is_requestor else 'hasPerformerAttestation'
                
                # Also update the attesterIds set
                user_id = attestation.get('user_id')
                
                await dynamodb.update_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    UpdateExpression=f"SET attestations = list_append(if_not_exists(attestations, :empty_list), :new_attestation), {condition_field} = :true, updatedAt = :now ADD attesterIds :user_id_set",
                    ConditionExpression=f"attribute_exists(questId) AND #status = :submitted_status AND {condition_field} = :false",
                    ExpressionAttributeNames={
                        '#status': 'status'
                    },
                    ExpressionAttributeValues={
                        ':new_attestation': {'L': [self._serialize_value(attestation)]},
                        ':empty_list': {'L': []},
                        ':user_id_set': {'SS': [user_id]},
                        ':true': {'BOOL': True},
                        ':false': {'BOOL': False},
                        ':submitted_status': {'S': 'SUBMITTED'},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
                return True
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Attestation already exists for {role} on quest {quest_id} or quest not in SUBMITTED state")
                return False
            logger.error(f"Error adding attestation atomically: {e}")
            raise
    
    async def claim_quest_atomic(self, quest_id: str, performer_id: str) -> bool:
        """Claim a quest atomically - prevents multiple performers"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    UpdateExpression="SET performerId = :pid, #s = :claimed_status, claimedAt = :now, updatedAt = :now",
                    ConditionExpression="#s = :open_status AND attribute_not_exists(performerId)",
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':pid': {'S': performer_id},
                        ':claimed_status': {'S': QuestStatus.CLAIMED.value},
                        ':open_status': {'S': QuestStatus.OPEN.value},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
                return True
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            logger.error(f"Error claiming quest atomically: {e}")
            raise
    
    async def submit_quest_atomic(self, quest_id: str, performer_id: str, submission_text: str) -> bool:
        """Submit a quest atomically"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    UpdateExpression="SET #s = :submitted_status, submittedAt = :now, updatedAt = :now, submissionText = :st",
                    ConditionExpression="#s = :claimed_status AND performerId = :pid",
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':submitted_status': {'S': QuestStatus.SUBMITTED.value},
                        ':claimed_status': {'S': QuestStatus.CLAIMED.value},
                        ':pid': {'S': performer_id},
                        ':now': {'S': datetime.utcnow().isoformat()},
                        ':st': {'S': submission_text}
                    }
                )
                return True
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            logger.error(f"Error submitting quest atomically: {e}")
            raise
    
    async def complete_quest_atomic(self, quest_id: str) -> bool:
        """Atomically mark a quest as COMPLETE"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    UpdateExpression="SET #S = :complete_status, completedAt = :now, updatedAt = :now",
                    ConditionExpression="#S = :submitted_status",
                    ExpressionAttributeNames={'#S': 'status'},
                    ExpressionAttributeValues={
                        ':complete_status': {'S': QuestStatus.COMPLETE.value},
                        ':submitted_status': {'S': QuestStatus.SUBMITTED.value},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            raise
    
    async def delete_quest_atomic(self, quest_id: str, user_id: str) -> bool:
        """Delete quest atomically - only if user is creator and quest is OPEN"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.delete_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    ConditionExpression="creatorId = :uid AND #s = :open_status",
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':uid': {'S': user_id},
                        ':open_status': {'S': QuestStatus.OPEN.value}
                    }
                )
                return True
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            logger.error(f"Error deleting quest atomically: {e}")
            raise
    
    async def dispute_quest_atomic(self, quest_id: str, user_id: str, reason: str) -> bool:
        """Atomically transition a quest to DISPUTED status"""
        try:
            async with self.get_resource() as dynamodb:
                await dynamodb.update_item(
                    TableName=self.quests_table_name,
                    Key={'questId': {'S': quest_id}},
                    UpdateExpression="SET #S = :disputed_status, disputeReason = :reason, updatedAt = :now",
                    ConditionExpression="#S = :submitted_status AND (creatorId = :uid OR performerId = :uid)",
                    ExpressionAttributeNames={'#S': 'status'},
                    ExpressionAttributeValues={
                        ':disputed_status': {'S': QuestStatus.DISPUTED.value},
                        ':submitted_status': {'S': QuestStatus.SUBMITTED.value},
                        ':reason': {'S': reason},
                        ':uid': {'S': user_id},
                        ':now': {'S': datetime.utcnow().isoformat()}
                    }
                )
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            logger.error(f"Error disputing quest {quest_id}: {e}")
            raise
    
    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to DynamoDB format"""
        result = {}
        for key, value in item.items():
            result[key] = self._serialize_value(value)
        return result
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """Convert Python value to DynamoDB format"""
        if value is None:
            return {'NULL': True}
        elif isinstance(value, bool):
            return {'BOOL': value}
        elif isinstance(value, (int, float)):
            return {'N': str(value)}
        elif isinstance(value, str):
            return {'S': value}
        elif isinstance(value, set):
            # Convert set to DynamoDB String Set
            return {'SS': list(value)}
        elif isinstance(value, list):
            return {'L': [self._serialize_value(v) for v in value]}
        elif isinstance(value, dict):
            return {'M': {k: self._serialize_value(v) for k, v in value.items()}}
        else:
            # Default to string representation
            return {'S': str(value)}
    
    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB format to Python dict"""
        result = {}
        for key, value in item.items():
            result[key] = self._deserialize_value(value)
        return result
    
    def _deserialize_value(self, value: Dict[str, Any]) -> Any:
        """Convert DynamoDB format to Python value"""
        if 'NULL' in value:
            return None
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'N' in value:
            # Try to return int if possible, otherwise float
            num_str = value['N']
            if '.' in num_str:
                return float(num_str)
            return int(num_str)
        elif 'S' in value:
            return value['S']
        elif 'SS' in value:
            # Convert DynamoDB String Set to Python set
            return set(value['SS'])
        elif 'L' in value:
            return [self._deserialize_value(v) for v in value['L']]
        elif 'M' in value:
            return {k: self._deserialize_value(v) for k, v in value['M'].items()}
        else:
            return None


# Create a singleton instance
db_client = DynamoDBClient()