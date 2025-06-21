"""
Rate limiting utility for preventing abuse of authentication endpoints
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")


class RateLimiter:
    """
    Rate limiter using DynamoDB for distributed rate limiting
    """
    
    def __init__(self, table_name: str = "civicforge-rate-limits"):
        self.table_name = table_name
        self.table = dynamodb.Table(table_name)
    
    def check_rate_limit(
        self,
        key: str,
        max_attempts: int,
        window_minutes: int,
        increment: bool = True
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if rate limit is exceeded and optionally increment counter
        
        Args:
            key: Unique identifier for rate limiting (e.g., "email_send:user@example.com")
            max_attempts: Maximum allowed attempts in the window
            window_minutes: Time window in minutes
            increment: Whether to increment the counter
            
        Returns:
            Tuple of (is_allowed, remaining_attempts)
        """
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(minutes=window_minutes)
            
            # Try to get existing rate limit record
            response = self.table.get_item(Key={"key": key})
            item = response.get("Item", {})
            
            # Clean up old attempts
            attempts = item.get("attempts", [])
            recent_attempts = [
                attempt for attempt in attempts
                if datetime.fromisoformat(attempt) > window_start
            ]
            
            # Check if limit exceeded
            if len(recent_attempts) >= max_attempts:
                logger.warning(f"Rate limit exceeded for key: {key}")
                return False, 0
            
            # Increment if requested
            if increment:
                recent_attempts.append(current_time.isoformat())
                
                # Update DynamoDB with new attempts
                self.table.put_item(
                    Item={
                        "key": key,
                        "attempts": recent_attempts,
                        "updated_at": current_time.isoformat(),
                        "ttl": int((current_time + timedelta(hours=1)).timestamp())
                    }
                )
            
            remaining = max_attempts - len(recent_attempts)
            return True, remaining
            
        except ClientError as e:
            logger.error(f"DynamoDB error in rate limiter: {e}")
            # Fail open - allow request if rate limiting fails
            return True, None
        except Exception as e:
            logger.error(f"Unexpected error in rate limiter: {e}")
            return True, None
    
    def reset_rate_limit(self, key: str) -> bool:
        """
        Reset rate limit for a specific key
        
        Args:
            key: The rate limit key to reset
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.table.delete_item(Key={"key": key})
            return True
        except ClientError as e:
            logger.error(f"Failed to reset rate limit for {key}: {e}")
            return False


# Singleton instance
_rate_limiter = None


def get_rate_limiter(table_name: Optional[str] = None) -> RateLimiter:
    """Get or create singleton rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(table_name or "civicforge-rate-limits")
    return _rate_limiter


# Convenience functions
def check_email_rate_limit(email: str, increment: bool = True) -> Tuple[bool, Optional[int]]:
    """Check rate limit for email sending"""
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(
        key=f"email_send:{email.lower()}",
        max_attempts=5,  # 5 emails per hour
        window_minutes=60,
        increment=increment
    )


def check_auth_rate_limit(identifier: str, increment: bool = True) -> Tuple[bool, Optional[int]]:
    """Check rate limit for authentication attempts"""
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(
        key=f"auth_attempt:{identifier}",
        max_attempts=10,  # 10 attempts per 15 minutes
        window_minutes=15,
        increment=increment
    )