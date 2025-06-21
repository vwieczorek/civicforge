"""
Verify Auth Challenge Response Lambda Trigger
Validates the email passcode submitted by the user
"""

import json
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Configuration
PASSCODES_TABLE_NAME = os.environ.get("PASSCODES_TABLE", "civicforge-passcodes")
MAX_ATTEMPTS = 3


def verify_passcode(email: str, submitted_passcode: str, table) -> tuple[bool, str]:
    """
    Verify the submitted passcode against stored value using atomic operations
    
    Returns:
        (is_valid, reason)
    """
    try:
        current_time = datetime.utcnow()
        
        # First, try to increment attempts atomically with conditions
        try:
            response = table.update_item(
                Key={"email": email},
                UpdateExpression="SET attempts = attempts + :inc",
                ConditionExpression="attribute_exists(email) AND attempts < :max_attempts AND expires_at > :now",
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":max_attempts": MAX_ATTEMPTS,
                    ":now": current_time.isoformat()
                },
                ReturnValues="ALL_NEW"
            )
            
            item = response["Attributes"]
            stored_passcode = item.get("passcode")
            attempts = item.get("attempts", 0)
            
            # Verify passcode
            if submitted_passcode == stored_passcode:
                # Success - delete the passcode atomically
                table.delete_item(
                    Key={"email": email},
                    ConditionExpression="passcode = :code",
                    ExpressionAttributeValues={":code": submitted_passcode}
                )
                return True, "VALID"
            else:
                # Check if this was the last allowed attempt
                if attempts >= MAX_ATTEMPTS:
                    # Delete after max attempts
                    table.delete_item(Key={"email": email})
                    return False, "MAX_ATTEMPTS_EXCEEDED"
                return False, "INVALID_PASSCODE"
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Check why the condition failed
                try:
                    item = table.get_item(Key={"email": email}).get("Item")
                    if not item:
                        return False, "NO_PASSCODE_FOUND"
                    
                    expires_at = item.get("expires_at")
                    if expires_at and datetime.fromisoformat(expires_at) < current_time:
                        # Delete expired passcode
                        table.delete_item(Key={"email": email})
                        return False, "PASSCODE_EXPIRED"
                    
                    attempts = item.get("attempts", 0)
                    if attempts >= MAX_ATTEMPTS:
                        # Delete after max attempts
                        table.delete_item(Key={"email": email})
                        return False, "MAX_ATTEMPTS_EXCEEDED"
                except:
                    return False, "NO_PASSCODE_FOUND"
            else:
                raise
            
    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return False, "VERIFICATION_ERROR"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False, "VERIFICATION_ERROR"


def record_security_event(email: str, event_type: str, success: bool, reason: str = None):
    """Record security events for monitoring and analysis"""
    # In production, this would write to CloudWatch Logs or a security event table
    logger.info(json.dumps({
        "event_type": "AUTH_VERIFICATION",
        "email": email,
        "verification_type": event_type,
        "success": success,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Verify auth challenge response Lambda trigger
    
    This function:
    1. Validates the submitted passcode
    2. Tracks attempt counts
    3. Handles expiration
    4. Records security events
    """
    logger.info(f"Verify auth challenge event: {json.dumps(event)}")
    
    # Extract request details
    request = event.get("request", {})
    user_attributes = request.get("userAttributes", {})
    email = user_attributes.get("email", "")
    
    # Get submitted answer
    challenge_answer = request.get("challengeAnswer", "")
    
    # Initialize response
    response = event.get("response", {})
    response["answerCorrect"] = False
    
    # The challengeName is not provided during VerifyAuthChallengeResponse
    # We need to check the private challenge parameters instead
    private_params = request.get("privateChallengeParameters", {})
    if not private_params.get("passcode"):
        logger.warning("No passcode in private challenge parameters")
        return event
    
    try:
        # Get DynamoDB table
        table = dynamodb.Table(PASSCODES_TABLE_NAME)
        
        # Verify the passcode
        is_valid, reason = verify_passcode(email, challenge_answer, table)
        
        # Set response
        response["answerCorrect"] = is_valid
        
        # Record security event
        record_security_event(
            email=email,
            event_type="EMAIL_PASSCODE",
            success=is_valid,
            reason=reason
        )
        
        # Add metadata for logging
        if not is_valid:
            logger.warning(f"Failed passcode verification for {email}: {reason}")
        else:
            logger.info(f"Successful passcode verification for {email}")
            
    except Exception as e:
        logger.error(f"Error verifying auth challenge: {e}")
        response["answerCorrect"] = False
        record_security_event(
            email=email,
            event_type="EMAIL_PASSCODE",
            success=False,
            reason="VERIFICATION_ERROR"
        )
    
    logger.info(f"Verify auth challenge response: {json.dumps(response)}")
    return event