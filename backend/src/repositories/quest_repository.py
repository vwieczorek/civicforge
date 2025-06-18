"""Quest repository for centralized quest data access with built-in safety."""
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from .base import BaseRepository
from ..models import Quest, QuestStatus, AttestationType


class QuestRepository(BaseRepository):
    """Centralized data access for quests with built-in safety patterns."""
    
    def __init__(self):
        """Initialize quest repository."""
        table_name = os.environ.get('QUESTS_TABLE', 'civicforge-quests')
        super().__init__(table_name)
        
    async def get_by_id(self, quest_id: str) -> Optional[Quest]:
        """Get quest by ID with proper error handling."""
        try:
            response = self.table.get_item(Key={'questId': quest_id})
            
            if 'Item' not in response:
                return None
            
            return Quest(**response['Item'])
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "get_quest")
            return None
    
    async def get_for_update(self, quest_id: str) -> Optional[Quest]:
        """Get quest with strong consistency for updates."""
        try:
            response = self.table.get_item(
                Key={'questId': quest_id},
                ConsistentRead=True
            )
            
            if 'Item' not in response:
                return None
            
            return Quest(**response['Item'])
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "get_quest_for_update")
            return None
    
    async def create_quest(self, quest: Quest) -> Quest:
        """Create new quest."""
        try:
            # Ensure timestamps are set
            now = datetime.utcnow().isoformat()
            quest_dict = quest.dict()
            quest_dict['createdAt'] = quest_dict.get('createdAt', now)
            quest_dict['updatedAt'] = quest_dict.get('updatedAt', now)
            
            self.table.put_item(Item=quest_dict)
            
            self.logger.info("quest_created", quest_id=quest.questId)
            return quest
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "create_quest")
            raise
    
    async def update_quest(self, quest: Quest) -> Quest:
        """Update quest (full replacement)."""
        try:
            quest_dict = quest.dict()
            quest_dict['updatedAt'] = datetime.utcnow().isoformat()
            
            self.table.put_item(Item=quest_dict)
            
            self.logger.info("quest_updated", quest_id=quest.questId)
            return quest
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "update_quest")
            raise
    
    async def list_by_status(
        self, 
        status: QuestStatus,
        page_size: int = 20,
        start_key: Optional[Dict] = None
    ) -> Tuple[List[Quest], Optional[Dict]]:
        """List quests by status using GSI, never scans."""
        try:
            query_params = {
                'IndexName': 'StatusIndex',
                'KeyConditionExpression': Key('status').eq(status.value),
                'Limit': page_size,
                'ScanIndexForward': False  # Newest first
            }
            
            if start_key:
                query_params['ExclusiveStartKey'] = start_key
            
            response = self.table.query(**query_params)
            
            quests = [Quest(**item) for item in response.get('Items', [])]
            next_key = response.get('LastEvaluatedKey')
            
            return quests, next_key
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # GSI doesn't exist, this should not happen in production
                self.logger.error("status_index_missing")
                return [], None
            
            await self._handle_dynamodb_error(e, "list_by_status")
            return [], None
    
    async def get_user_quests(
        self,
        user_id: str,
        role: str = 'creator',
        page_size: int = 20,
        start_key: Optional[Dict] = None
    ) -> Tuple[List[Quest], Optional[Dict]]:
        """Get quests for a user with role-based filtering."""
        try:
            if role == 'creator':
                index_name = 'CreatorIndex'
                key_attr = 'creatorId'
            elif role == 'performer':
                index_name = 'PerformerIndex'
                key_attr = 'performerId'
            else:
                raise ValueError(f"Invalid role: {role}")
            
            query_params = {
                'IndexName': index_name,
                'KeyConditionExpression': Key(key_attr).eq(user_id),
                'Limit': page_size,
                'ScanIndexForward': False  # Newest first
            }
            
            if start_key:
                query_params['ExclusiveStartKey'] = start_key
            
            response = self.table.query(**query_params)
            
            quests = [Quest(**item) for item in response.get('Items', [])]
            next_key = response.get('LastEvaluatedKey')
            
            return quests, next_key
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, f"get_user_quests_{role}")
            return [], None
    
    async def claim_quest(self, quest_id: str, performer_id: str) -> bool:
        """Atomically claim a quest, preventing double claiming."""
        try:
            self.table.update_item(
                Key={'questId': quest_id},
                UpdateExpression='SET performerId = :pid, #s = :claimed_status, claimedAt = :now, updatedAt = :now',
                ConditionExpression='#s = :open_status AND (attribute_not_exists(performerId) OR performerId = :null)',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':pid': performer_id,
                    ':claimed_status': QuestStatus.CLAIMED.value,
                    ':open_status': QuestStatus.OPEN.value,
                    ':null': None,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "quest_claimed",
                quest_id=quest_id,
                performer_id=performer_id
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "quest_claim_failed",
                    quest_id=quest_id,
                    performer_id=performer_id,
                    reason="Already claimed or not open"
                )
                return False
            
            await self._handle_dynamodb_error(e, "claim_quest")
            return False
    
    async def submit_quest(
        self, 
        quest_id: str, 
        performer_id: str,
        submission_text: str
    ) -> bool:
        """Submit quest completion, ensuring only performer can submit."""
        try:
            self.table.update_item(
                Key={'questId': quest_id},
                UpdateExpression='SET #s = :submitted_status, submittedAt = :now, submissionText = :st, updatedAt = :now',
                ConditionExpression='#s = :claimed_status AND performerId = :pid',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':submitted_status': QuestStatus.SUBMITTED.value,
                    ':claimed_status': QuestStatus.CLAIMED.value,
                    ':pid': performer_id,
                    ':st': submission_text,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "quest_submitted",
                quest_id=quest_id,
                performer_id=performer_id
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "quest_submit_failed",
                    quest_id=quest_id,
                    performer_id=performer_id,
                    reason="Not claimed by user or wrong status"
                )
                return False
            
            await self._handle_dynamodb_error(e, "submit_quest")
            return False
    
    async def add_attestation(
        self,
        quest_id: str,
        user_id: str,
        attestation_type: AttestationType,
        attestation_data: Dict[str, Any]
    ) -> bool:
        """Add attestation atomically, preventing duplicates."""
        try:
            # Determine which flag to set based on attestation type
            condition_field = (
                'hasRequestorAttestation' if attestation_type == AttestationType.REQUESTOR
                else 'hasPerformerAttestation'
            )
            
            # Build attestation object
            attestation = {
                'userId': user_id,
                'type': attestation_type.value,
                'timestamp': datetime.utcnow().isoformat(),
                **attestation_data
            }
            
            self.table.update_item(
                Key={'questId': quest_id},
                UpdateExpression=f'SET attestations = list_append(attestations, :attestation), {condition_field} = :true, updatedAt = :now ADD attesterIds :user_id_set',
                ConditionExpression='#status = :submitted_status AND NOT contains(attesterIds, :user_id)',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':attestation': [attestation],
                    ':true': True,
                    ':submitted_status': QuestStatus.SUBMITTED.value,
                    ':user_id': user_id,
                    ':user_id_set': {user_id},  # String Set
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "attestation_added",
                quest_id=quest_id,
                user_id=user_id,
                attestation_type=attestation_type.value
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "attestation_failed",
                    quest_id=quest_id,
                    user_id=user_id,
                    reason="Already attested or wrong status"
                )
                return False
            
            await self._handle_dynamodb_error(e, "add_attestation")
            return False
    
    async def complete_quest(self, quest_id: str) -> bool:
        """Complete quest atomically, ensuring both attestations exist."""
        try:
            self.table.update_item(
                Key={'questId': quest_id},
                UpdateExpression='SET #S = :complete_status, completedAt = :now, updatedAt = :now',
                ConditionExpression='#S = :submitted_status AND hasRequestorAttestation = :true AND hasPerformerAttestation = :true',
                ExpressionAttributeNames={'#S': 'status'},
                ExpressionAttributeValues={
                    ':complete_status': QuestStatus.COMPLETED.value,
                    ':submitted_status': QuestStatus.SUBMITTED.value,
                    ':true': True,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info("quest_completed", quest_id=quest_id)
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "quest_complete_failed",
                    quest_id=quest_id,
                    reason="Missing attestations or wrong status"
                )
                return False
            
            await self._handle_dynamodb_error(e, "complete_quest")
            return False
    
    async def dispute_quest(
        self,
        quest_id: str,
        user_id: str,
        dispute_reason: str
    ) -> bool:
        """Dispute quest, ensuring user is involved party."""
        try:
            self.table.update_item(
                Key={'questId': quest_id},
                UpdateExpression='SET #S = :disputed_status, disputeReason = :reason, updatedAt = :now',
                ConditionExpression='#S = :submitted_status AND (creatorId = :uid OR performerId = :uid)',
                ExpressionAttributeNames={'#S': 'status'},
                ExpressionAttributeValues={
                    ':disputed_status': QuestStatus.DISPUTED.value,
                    ':submitted_status': QuestStatus.SUBMITTED.value,
                    ':uid': user_id,
                    ':reason': dispute_reason,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "quest_disputed",
                quest_id=quest_id,
                user_id=user_id
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "quest_dispute_failed",
                    quest_id=quest_id,
                    user_id=user_id,
                    reason="User not involved or wrong status"
                )
                return False
            
            await self._handle_dynamodb_error(e, "dispute_quest")
            return False
    
    async def delete_quest(self, quest_id: str, creator_id: str) -> bool:
        """Delete quest atomically, ensuring only creator can delete open quests."""
        try:
            self.table.delete_item(
                Key={'questId': quest_id},
                ConditionExpression='creatorId = :uid AND #s = :open_status',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':uid': creator_id,
                    ':open_status': QuestStatus.OPEN.value
                }
            )
            
            self.logger.info(
                "quest_deleted",
                quest_id=quest_id,
                creator_id=creator_id
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "quest_delete_failed",
                    quest_id=quest_id,
                    creator_id=creator_id,
                    reason="Not creator or not open"
                )
                return False
            
            await self._handle_dynamodb_error(e, "delete_quest")
            return False