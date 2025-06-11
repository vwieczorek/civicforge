"""
DynamoDB client for quest and user operations
"""

import os
import boto3
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .models import Quest, User


class DynamoDBClient:
    """Minimal DynamoDB operations for dual-attestation"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.users_table = self.dynamodb.Table(
            os.environ.get("USERS_TABLE", "civicforge-users")
        )
        self.quests_table = self.dynamodb.Table(
            os.environ.get("QUESTS_TABLE", "civicforge-quests")
        )
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            response = self.users_table.get_item(Key={'userId': user_id})
            if 'Item' in response:
                return User(**response['Item'])
            return None
        except ClientError as e:
            print(f"Error getting user: {e}")
            return None
    
    async def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get quest by ID"""
        try:
            response = self.quests_table.get_item(Key={'questId': quest_id})
            if 'Item' in response:
                return Quest(**response['Item'])
            return None
        except ClientError as e:
            print(f"Error getting quest: {e}")
            return None
    
    async def update_quest(self, quest: Quest) -> None:
        """Update quest in database"""
        try:
            # Convert quest to dict, handling datetime serialization
            quest_dict = quest.dict()
            for key, value in quest_dict.items():
                if isinstance(value, datetime):
                    quest_dict[key] = value.isoformat()
                elif isinstance(value, list) and key == 'attestations':
                    # Serialize attestations
                    quest_dict[key] = [
                        {**a, 'attested_at': a['attested_at'].isoformat()}
                        for a in value
                    ]
            
            quest_dict['updatedAt'] = datetime.utcnow().isoformat()
            
            self.quests_table.put_item(Item=quest_dict)
            
        except ClientError as e:
            print(f"Error updating quest: {e}")
            raise
    
    async def award_rewards(
        self, 
        user_id: str, 
        xp: int, 
        reputation: int
    ) -> None:
        """Award XP and reputation to user"""
        try:
            self.users_table.update_item(
                Key={'userId': user_id},
                UpdateExpression="ADD experience :xp, reputation :rep",
                ExpressionAttributeValues={
                    ':xp': xp,
                    ':rep': reputation
                }
            )
        except ClientError as e:
            print(f"Error awarding rewards: {e}")
            # Don't fail the quest completion if reward fails
            pass
    
    async def create_quest(self, quest_data: Dict[str, Any]) -> Quest:
        """Create a new quest"""
        quest_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        quest = Quest(
            questId=quest_id,
            createdAt=timestamp,
            **quest_data
        )
        
        await self.update_quest(quest)
        return quest


# Global client instance
db_client = DynamoDBClient()