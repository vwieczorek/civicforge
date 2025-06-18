"""
DLQ Re-processor for failed reward operations with idempotency and lease system
Runs on a schedule to retry failed reward distributions
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
USERS_TABLE = os.environ['USERS_TABLE']
FAILED_REWARDS_TABLE = os.environ['FAILED_REWARDS_TABLE']
MAX_RETRY_ATTEMPTS = int(os.environ.get('MAX_RETRY_ATTEMPTS', '5'))
LEASE_DURATION_SECONDS = int(os.environ.get('LEASE_DURATION_SECONDS', '300'))  # 5 minutes

# DynamoDB client
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE)
failed_rewards_table = dynamodb.Table(FAILED_REWARDS_TABLE)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process failed rewards from the DLQ table with idempotency
    
    Args:
        event: CloudWatch Events scheduled event
        context: Lambda context
    
    Returns:
        Summary of processing results
    """
    logger.info(f"Starting failed rewards reprocessing at {datetime.now(timezone.utc).isoformat()}")
    
    processed = 0
    succeeded = 0
    failed = 0
    abandoned = 0
    skipped = 0
    
    try:
        # Query for pending failed rewards that are not currently being processed
        current_time = datetime.now(timezone.utc)
        response = failed_rewards_table.query(
            IndexName='status-createdAt-index',
            KeyConditionExpression=Key('status').eq('pending'),
            Limit=100  # Process up to 100 items per run
        )
        
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} pending rewards to process")
        
        for item in items:
            processed += 1
            reward_id = item['rewardId']
            
            # Try to acquire a lease on this reward
            if not acquire_lease(reward_id, current_time):
                logger.info(f"Reward {reward_id} is being processed by another worker, skipping")
                skipped += 1
                continue
            
            try:
                # Process the reward with the lease
                result = process_reward_with_lease(item, current_time)
                if result == 'succeeded':
                    succeeded += 1
                elif result == 'abandoned':
                    abandoned += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error processing reward {reward_id}: {str(e)}")
                failed += 1
                # Release the lease on error
                release_lease(reward_id)
    
    except Exception as e:
        logger.error(f"Error querying failed rewards table: {str(e)}")
        raise
    
    summary = {
        'processed': processed,
        'succeeded': succeeded,
        'failed': failed,
        'abandoned': abandoned,
        'skipped': skipped,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(f"Reprocessing complete: {json.dumps(summary)}")
    return summary


def acquire_lease(reward_id: str, current_time: datetime) -> bool:
    """
    Try to acquire a lease on a reward for processing
    
    Returns True if lease acquired, False if already leased
    """
    lease_expiry = current_time + timedelta(seconds=LEASE_DURATION_SECONDS)
    
    try:
        failed_rewards_table.update_item(
            Key={'rewardId': reward_id},
            UpdateExpression='SET leaseOwner = :owner, leaseExpiresAt = :expiry',
            ConditionExpression=(
                'attribute_not_exists(leaseOwner) OR '
                'leaseExpiresAt < :current_time OR '
                'leaseOwner = :none'
            ),
            ExpressionAttributeValues={
                ':owner': os.environ.get('AWS_LAMBDA_REQUEST_ID', 'local-test'),
                ':expiry': lease_expiry.isoformat(),
                ':current_time': current_time.isoformat(),
                ':none': None
            }
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False
        raise


def release_lease(reward_id: str) -> None:
    """Release the lease on a reward"""
    try:
        failed_rewards_table.update_item(
            Key={'rewardId': reward_id},
            UpdateExpression='REMOVE leaseOwner, leaseExpiresAt'
        )
    except Exception as e:
        logger.warning(f"Failed to release lease for {reward_id}: {str(e)}")


def process_reward_with_lease(item: Dict[str, Any], current_time: datetime) -> str:
    """
    Process a reward with an active lease
    
    Returns: 'succeeded', 'abandoned', or 'failed'
    """
    reward_id = item['rewardId']
    user_id = item['userId']
    retry_count = item.get('retryCount', 0)
    
    logger.info(f"Processing reward {reward_id} for user {user_id}, retry attempt {retry_count + 1}")
    
    # Check if we've exceeded max retries
    if retry_count >= MAX_RETRY_ATTEMPTS:
        logger.warning(f"Reward {reward_id} exceeded max retries, marking as abandoned")
        update_reward_status(reward_id, 'abandoned', retry_count)
        return 'abandoned'
    
    # Check for idempotency - has this reward already been processed?
    if is_reward_already_processed(user_id, reward_id):
        logger.info(f"Reward {reward_id} already processed for user {user_id}, marking as resolved")
        update_reward_status(reward_id, 'resolved', retry_count)
        return 'succeeded'
    
    # Attempt to award the rewards atomically
    try:
        success = award_rewards_idempotently(
            user_id=user_id,
            reward_id=reward_id,
            xp_amount=item.get('xpAmount', 0),
            reputation_amount=item.get('reputationAmount', 0),
            quest_points_amount=item.get('questPointsAmount', 0)
        )
        
        if success:
            # Mark as resolved
            update_reward_status(reward_id, 'resolved', retry_count + 1)
            logger.info(f"Successfully processed reward {reward_id}")
            return 'succeeded'
        else:
            # Update retry count but keep as pending
            update_reward_status(reward_id, 'pending', retry_count + 1)
            return 'failed'
            
    except Exception as e:
        logger.error(f"Failed to process reward {reward_id}: {str(e)}")
        # Update retry count
        update_reward_status(reward_id, 'pending', retry_count + 1)
        return 'failed'


def is_reward_already_processed(user_id: str, reward_id: str) -> bool:
    """Check if a reward has already been processed for a user"""
    try:
        response = users_table.get_item(
            Key={'userId': user_id},
            ProjectionExpression='processedRewardIds'
        )
        
        if 'Item' in response:
            processed_ids = response['Item'].get('processedRewardIds', set())
            return reward_id in processed_ids
        return False
    except Exception as e:
        logger.error(f"Error checking processed rewards for user {user_id}: {str(e)}")
        return False


def award_rewards_idempotently(
    user_id: str,
    reward_id: str,
    xp_amount: int,
    reputation_amount: int,
    quest_points_amount: int
) -> bool:
    """
    Award rewards to a user idempotently using conditional updates
    
    Returns True if rewards were awarded, False if already processed
    """
    try:
        # Build update expression dynamically based on what needs to be awarded
        set_parts = []
        expression_values = {':reward_id_set': {reward_id}, ':reward_id_str': reward_id}
        
        if xp_amount > 0:
            set_parts.append('experience = experience + :xp')
            expression_values[':xp'] = xp_amount
            
        if reputation_amount > 0:
            set_parts.append('reputation = reputation + :rep')
            expression_values[':rep'] = reputation_amount
            
        if quest_points_amount > 0:
            set_parts.append('questCreationPoints = questCreationPoints + :qp')
            expression_values[':qp'] = quest_points_amount
        
        # Build complete update expression
        update_expression = ''
        if set_parts:
            update_expression = 'SET ' + ', '.join(set_parts) + ' '
        update_expression += 'ADD processedRewardIds :reward_id_set'
        
        # Perform the update with condition
        users_table.update_item(
            Key={'userId': user_id},
            UpdateExpression=update_expression,
            ConditionExpression=(
                'attribute_exists(userId) AND '
                '(attribute_not_exists(processedRewardIds) OR NOT contains(processedRewardIds, :reward_id_str))'
            ),
            ExpressionAttributeValues=expression_values
        )
        
        logger.info(f"Successfully awarded rewards for {reward_id} to user {user_id}")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(f"Reward {reward_id} already processed for user {user_id}")
            return True  # Consider it successful since the reward was already applied
        else:
            logger.error(f"Failed to award rewards for {reward_id}: {str(e)}")
            raise


def update_reward_status(reward_id: str, status: str, retry_count: int) -> None:
    """Update the status and retry count of a failed reward"""
    try:
        update_expr = 'SET #status = :status, retryCount = :count, lastRetryAt = :timestamp'
        expr_values = {
            ':status': status,
            ':count': retry_count,
            ':timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if status in ['resolved', 'abandoned']:
            update_expr += ', resolvedAt = :resolved_at, leaseOwner = :none, leaseExpiresAt = :none'
            expr_values[':resolved_at'] = datetime.now(timezone.utc).isoformat()
            expr_values[':none'] = None
        
        failed_rewards_table.update_item(
            Key={'rewardId': reward_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expr_values
        )
    except Exception as e:
        logger.error(f"Failed to update reward status for {reward_id}: {str(e)}")
        raise