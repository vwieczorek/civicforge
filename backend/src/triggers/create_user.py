"""
Cognito PostConfirmation trigger to create user records in DynamoDB.

This Lambda function is triggered when a user confirms their account in Cognito.
It creates a corresponding user record in the application's DynamoDB users table.
"""

import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import idempotency decorator
try:
    from ..utils.idempotency import user_creation_idempotent
except ImportError:
    # Fallback if idempotency not available
    def user_creation_idempotent(func):
        return func

# Environment variables
INITIAL_POINTS = int(os.environ.get("INITIAL_QUEST_CREATION_POINTS", "10"))
USERS_TABLE = os.environ.get("USERS_TABLE_NAME")
if not USERS_TABLE:
    raise ValueError("Missing required environment variable: USERS_TABLE_NAME")

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(USERS_TABLE)


@user_creation_idempotent
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Cognito PostConfirmation trigger handler.
    
    Creates a user record in DynamoDB when a user confirms their Cognito account.
    Designed to be idempotent and fail gracefully to avoid blocking user signup.
    
    Args:
        event: Cognito PostConfirmation trigger event
        context: Lambda context object
        
    Returns:
        The original event object (required by Cognito)
    """
    try:
        # Extract user information from Cognito event
        user_attributes = event['request']['userAttributes']
        user_id = user_attributes['sub']
        username = event['userName']
        email = user_attributes.get('email')
        
        logger.info(f"Processing PostConfirmation for user: {user_id}")
        
        # Prepare user record based on User model in models.py
        timestamp = datetime.utcnow().isoformat()
        user_item = {
            'userId': user_id,
            'username': username,
            'reputation': 0,
            'experience': 0,
            'questCreationPoints': INITIAL_POINTS,
            'createdAt': timestamp,
            'updatedAt': timestamp
        }
        
        # Add optional fields if available
        if email:
            user_item['email'] = email
            
        # Create the user record atomically with idempotency check
        table.put_item(
            Item=user_item,
            ConditionExpression='attribute_not_exists(userId)'
        )
        
        logger.info(f"Successfully created user record for {user_id}")
        
    except ClientError as e:
        # If the user already exists, the conditional check will fail
        # This is expected and means the function is idempotent
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(f"User {user_id} already exists. Skipping creation.")
        else:
            # For any other boto3 error, log it for the DLQ
            logger.error(f"Failed to create user record due to a client error: {str(e)}", exc_info=True)
            logger.error(f"Event payload: {json.dumps(event, default=str)}")
        
    except Exception as e:
        # Log the error but DO NOT re-raise to avoid blocking user signup
        # Failed user creations will be handled via DLQ and monitoring
        logger.error(f"Failed to create user record: {str(e)}", exc_info=True)
        logger.error(f"Event payload: {json.dumps(event, default=str)}")
        
        # For MVP: Let signup succeed even if DB write fails
        # Production monitoring will catch these failures via DLQ
    
    # Always return the event to Cognito (required)
    return event