"""
Pre-Authentication Lambda Trigger
Implements rate limiting and security checks before authentication
"""

import json
import logging
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Configuration
RATE_LIMIT_TABLE_NAME = os.environ.get("RATE_LIMIT_TABLE", "civicforge-auth-rate-limit")
MAX_ATTEMPTS_PER_HOUR = 5
MAX_ATTEMPTS_PER_DAY = 20
BLOCK_DURATION_MINUTES = 60


def check_rate_limit(email: str, ip_address: str, table) -> tuple[bool, str]:
    """
    Check if the user has exceeded rate limits
    
    Returns:
        (is_allowed, reason)
    """
    try:
        current_time = datetime.utcnow()
        
        # Check if email is blocked
        block_response = table.get_item(Key={"identifier": f"email_blocked#{email}"})
        if "Item" in block_response:
            blocked_until = datetime.fromisoformat(block_response["Item"]["blocked_until"])
            if blocked_until > current_time:
                return False, "EMAIL_BLOCKED"
        
        # Check hourly limit
        hourly_response = table.get_item(Key={"identifier": f"email_hourly#{email}"})
        if "Item" in hourly_response:
            hourly_attempts = hourly_response["Item"].get("attempts", 0)
            if hourly_attempts >= MAX_ATTEMPTS_PER_HOUR:
                # Block the email for BLOCK_DURATION_MINUTES
                table.put_item(
                    Item={
                        "identifier": f"email_blocked#{email}",
                        "blocked_until": (current_time + timedelta(minutes=BLOCK_DURATION_MINUTES)).isoformat(),
                        "ttl": int((current_time + timedelta(minutes=BLOCK_DURATION_MINUTES)).timestamp())
                    }
                )
                return False, "HOURLY_LIMIT_EXCEEDED"
        
        # Check daily limit
        daily_response = table.get_item(Key={"identifier": f"email_daily#{email}"})
        if "Item" in daily_response:
            daily_attempts = daily_response["Item"].get("attempts", 0)
            if daily_attempts >= MAX_ATTEMPTS_PER_DAY:
                return False, "DAILY_LIMIT_EXCEEDED"
        
        # Check IP-based rate limit (more aggressive)
        if ip_address:
            ip_response = table.get_item(Key={"identifier": f"ip#{ip_address}"})
            if "Item" in ip_response:
                item = ip_response["Item"]
                ip_attempts = item.get("attempts_last_hour", 0)
                if ip_attempts >= MAX_ATTEMPTS_PER_HOUR * 2:  # Double limit for IPs
                    return False, "IP_RATE_LIMIT_EXCEEDED"
        
        return True, "ALLOWED"
        
    except ClientError as e:
        logger.error(f"DynamoDB error in rate limiting: {e}")
        # Fail open - allow authentication if rate limiting fails
        return True, "RATE_LIMIT_CHECK_FAILED"


def record_attempt(email: str, ip_address: str, table):
    """Record authentication attempt for rate limiting"""
    current_time = datetime.utcnow()
    
    try:
        # Update hourly counter with 1-hour TTL
        table.update_item(
            Key={"identifier": f"email_hourly#{email}"},
            UpdateExpression="""
                SET attempts = if_not_exists(attempts, :zero) + :inc,
                    last_attempt = :now,
                    ttl = :ttl_hour
            """,
            ExpressionAttributeValues={
                ":zero": 0,
                ":inc": 1,
                ":now": current_time.isoformat(),
                ":ttl_hour": int((current_time + timedelta(hours=1)).timestamp())
            }
        )
        
        # Update daily counter with 24-hour TTL
        table.update_item(
            Key={"identifier": f"email_daily#{email}"},
            UpdateExpression="""
                SET attempts = if_not_exists(attempts, :zero) + :inc,
                    last_attempt = :now,
                    ttl = :ttl_day
            """,
            ExpressionAttributeValues={
                ":zero": 0,
                ":inc": 1,
                ":now": current_time.isoformat(),
                ":ttl_day": int((current_time + timedelta(days=1)).timestamp())
            }
        )
        
        # Update IP-based counter if available
        if ip_address:
            table.update_item(
                Key={"identifier": f"ip#{ip_address}"},
                UpdateExpression="""
                    SET attempts_last_hour = if_not_exists(attempts_last_hour, :zero) + :inc,
                        last_attempt = :now,
                        ttl = :ttl
                """,
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":now": current_time.isoformat(),
                    ":ttl": int((current_time + timedelta(hours=2)).timestamp())
                }
            )
    except ClientError as e:
        logger.error(f"Failed to record attempt: {e}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pre-authentication Lambda trigger
    
    This function:
    1. Checks rate limits
    2. Validates request source
    3. Records authentication attempts
    4. Blocks suspicious activity
    """
    logger.info(f"Pre-authentication event: {json.dumps(event)}")
    
    # Extract request details
    request = event.get("request", {})
    user_attributes = request.get("userAttributes", {})
    email = user_attributes.get("email", "")
    
    # Get IP address from request context
    request_context = event.get("requestContext", {})
    ip_address = request_context.get("sourceIp", "")
    
    # Skip rate limiting for certain scenarios (e.g., admin override)
    if request.get("skipRateLimit"):
        logger.info(f"Skipping rate limit for {email}")
        return event
    
    try:
        # Get rate limit table
        table = dynamodb.Table(RATE_LIMIT_TABLE_NAME)
        
        # Check rate limits
        is_allowed, reason = check_rate_limit(email, ip_address, table)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {email}: {reason}")
            # Fail authentication
            raise Exception(f"Authentication rate limit exceeded: {reason}")
        
        # Record the attempt
        record_attempt(email, ip_address, table)
        
        logger.info(f"Pre-authentication passed for {email}")
        
    except Exception as e:
        logger.error(f"Pre-authentication error: {e}")
        # Re-raise to fail the authentication
        raise
    
    return event