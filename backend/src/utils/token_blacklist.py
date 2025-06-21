"""
Token blacklist utility for session revocation
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")


class TokenBlacklist:
    """
    Manages revoked tokens using DynamoDB
    """
    
    def __init__(self, table_name: str = "civicforge-token-blacklist"):
        self.table_name = table_name
        self.table = dynamodb.Table(table_name)
    
    def revoke_token(self, token_jti: str, user_id: str, exp_timestamp: int, reason: str = "user_logout") -> bool:
        """
        Add a token to the blacklist
        
        Args:
            token_jti: JWT ID (jti claim) of the token
            user_id: User ID associated with the token
            exp_timestamp: Token expiration timestamp (for TTL)
            reason: Reason for revocation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.table.put_item(
                Item={
                    "jti": token_jti,
                    "user_id": user_id,
                    "revoked_at": datetime.utcnow().isoformat(),
                    "reason": reason,
                    "ttl": exp_timestamp + 3600  # Keep for 1 hour after token expires
                }
            )
            
            logger.info(f"Token revoked: jti={token_jti}, user={user_id}, reason={reason}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def is_token_revoked(self, token_jti: str) -> bool:
        """
        Check if a token is in the blacklist
        
        Args:
            token_jti: JWT ID to check
            
        Returns:
            True if token is revoked, False otherwise
        """
        try:
            response = self.table.get_item(Key={"jti": token_jti})
            return "Item" in response
            
        except ClientError as e:
            logger.error(f"Failed to check token blacklist: {e}")
            # Fail closed - treat as revoked if we can't check
            return True
    
    def revoke_all_user_tokens(self, user_id: str, before_timestamp: Optional[int] = None) -> int:
        """
        Revoke all tokens for a user (requires GSI on user_id)
        
        Args:
            user_id: User whose tokens to revoke
            before_timestamp: Only revoke tokens issued before this timestamp
            
        Returns:
            Number of tokens revoked
        """
        try:
            # This would require a GSI on user_id in production
            # For now, we'll log the intent
            logger.warning(f"Bulk token revocation requested for user {user_id}")
            
            # In a real implementation, you would:
            # 1. Query the user's active sessions table
            # 2. Extract all JTIs
            # 3. Add them to the blacklist
            # 4. Clear the sessions
            
            return 0
            
        except ClientError as e:
            logger.error(f"Failed to revoke user tokens: {e}")
            return 0
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from the blacklist
        This is handled automatically by DynamoDB TTL, but can be called manually
        
        Returns:
            Number of entries cleaned up
        """
        # DynamoDB TTL handles this automatically
        # This method is here for manual cleanup if needed
        return 0


# Singleton instance
_token_blacklist = None


def get_token_blacklist(table_name: Optional[str] = None) -> TokenBlacklist:
    """Get or create singleton token blacklist instance"""
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist(table_name or "civicforge-token-blacklist")
    return _token_blacklist


# Convenience functions
def revoke_token(token_jti: str, user_id: str, exp_timestamp: int, reason: str = "user_logout") -> bool:
    """Revoke a specific token"""
    blacklist = get_token_blacklist()
    return blacklist.revoke_token(token_jti, user_id, exp_timestamp, reason)


def is_token_revoked(token_jti: str) -> bool:
    """Check if a token is revoked"""
    blacklist = get_token_blacklist()
    return blacklist.is_token_revoked(token_jti)


def generate_jti() -> str:
    """
    Generate a unique JWT ID for new tokens
    This should be called when creating tokens to enable revocation
    """
    import uuid
    return str(uuid.uuid4())