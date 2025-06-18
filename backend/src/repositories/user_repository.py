"""User repository for centralized user data access with built-in safety."""
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError

from .base import BaseRepository
from ..models import User


class UserRepository(BaseRepository):
    """Centralized data access for users with built-in safety patterns."""
    
    def __init__(self):
        """Initialize user repository."""
        table_name = os.environ.get('USERS_TABLE', 'civicforge-users')
        super().__init__(table_name)
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID with proper error handling."""
        try:
            response = self.table.get_item(Key={'userId': user_id})
            
            if 'Item' not in response:
                return None
            
            return User(**response['Item'])
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "get_user")
            return None
    
    async def create_user(self, user: User) -> User:
        """Create user with idempotency check."""
        try:
            # Ensure timestamps are set
            now = datetime.utcnow().isoformat()
            user_dict = user.dict()
            user_dict['createdAt'] = user_dict.get('createdAt', now)
            user_dict['updatedAt'] = user_dict.get('updatedAt', now)
            
            # Create with idempotency condition
            self.table.put_item(
                Item=user_dict,
                ConditionExpression='attribute_not_exists(userId)'
            )
            
            self.logger.info("user_created", user_id=user.userId)
            return user
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # User already exists, return existing user
                existing = await self.get_by_id(user.userId)
                if existing:
                    return existing
                raise ValueError(f"User {user.userId} already exists")
            
            await self._handle_dynamodb_error(e, "create_user")
            raise
    
    async def award_rewards(self, user_id: str, xp: int, reputation: int) -> bool:
        """Award XP and reputation atomically."""
        try:
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression='ADD experience :xp, reputation :rep SET updatedAt = :now',
                ExpressionAttributeValues={
                    ':xp': Decimal(str(xp)),
                    ':rep': Decimal(str(reputation)),
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "rewards_awarded",
                user_id=user_id,
                xp=xp,
                reputation=reputation
            )
            return True
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "award_rewards")
            return False
    
    async def deduct_quest_points(self, user_id: str, points: int) -> bool:
        """Deduct quest creation points with balance check."""
        try:
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression='SET questCreationPoints = questCreationPoints - :points, updatedAt = :now',
                ConditionExpression='questCreationPoints >= :points',
                ExpressionAttributeValues={
                    ':points': Decimal(str(points)),
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "quest_points_deducted",
                user_id=user_id,
                points=points
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.warning(
                    "insufficient_quest_points",
                    user_id=user_id,
                    requested_points=points
                )
                return False
            
            await self._handle_dynamodb_error(e, "deduct_quest_points")
            return False
    
    async def award_quest_points(self, user_id: str, points: int) -> bool:
        """Award quest creation points (for refunds)."""
        try:
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression='ADD questCreationPoints :points SET updatedAt = :now',
                ExpressionAttributeValues={
                    ':points': Decimal(str(points)),
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "quest_points_awarded",
                user_id=user_id,
                points=points
            )
            return True
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "award_quest_points")
            return False
    
    async def update_wallet_address(self, user_id: str, wallet_address: str) -> bool:
        """Update user's wallet address."""
        try:
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression='SET walletAddress = :addr, updatedAt = :now',
                ExpressionAttributeValues={
                    ':addr': wallet_address,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                "wallet_address_updated",
                user_id=user_id,
                wallet_address=wallet_address
            )
            return True
            
        except ClientError as e:
            await self._handle_dynamodb_error(e, "update_wallet_address")
            return False
    
    async def award_rewards_idempotently(
        self, 
        user_id: str, 
        reward_id: str,
        xp: int, 
        reputation: int
    ) -> bool:
        """Award rewards idempotently using processedRewardIds set."""
        try:
            # Build update expression dynamically
            update_parts = []
            expr_values = {
                ':reward_id_set': {reward_id},  # DynamoDB String Set
                ':reward_id_str': reward_id,    # For contains check
                ':now': datetime.utcnow().isoformat()
            }
            
            if xp > 0:
                update_parts.append('experience = experience + :xp')
                expr_values[':xp'] = Decimal(str(xp))
            
            if reputation > 0:
                update_parts.append('reputation = reputation + :rep')
                expr_values[':rep'] = Decimal(str(reputation))
            
            update_parts.append('updatedAt = :now')
            
            # Add reward ID to processed set
            update_expr = f"SET {', '.join(update_parts)} ADD processedRewardIds :reward_id_set"
            
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression=update_expr,
                ConditionExpression='NOT contains(processedRewardIds, :reward_id_str)',
                ExpressionAttributeValues=expr_values
            )
            
            self.logger.info(
                "rewards_awarded_idempotently",
                user_id=user_id,
                reward_id=reward_id,
                xp=xp,
                reputation=reputation
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                self.logger.info(
                    "reward_already_processed",
                    user_id=user_id,
                    reward_id=reward_id
                )
                return True  # Already processed, consider it success
            
            await self._handle_dynamodb_error(e, "award_rewards_idempotently")
            return False
    
    async def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user statistics summary."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        return {
            'userId': user.userId,
            'username': user.username,
            'reputation': int(user.reputation),
            'experience': int(user.experience),
            'questCreationPoints': int(user.questCreationPoints),
            'walletAddress': getattr(user, 'walletAddress', None)
        }