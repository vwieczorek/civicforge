"""Authentication utilities for CivicForge Board MVP."""

from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib
import hmac
import secrets
import json
import base64
import os

# Simple JWT implementation (for MVP - consider using PyJWT in production)
SECRET_KEY = os.environ.get('CIVICFORGE_SECRET_KEY', 'dev-secret-key-change-in-production')
TOKEN_EXPIRY_HOURS = int(os.environ.get('TOKEN_EXPIRY_HOURS', '24'))


def hash_password(password: str) -> str:
    """Hash a password using SHA256 with salt."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                   password.encode('utf-8'), 
                                   salt.encode('utf-8'), 
                                   100000)
    return f"{salt}${pwdhash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    if not password_hash:
        return False
    try:
        salt, pwdhash_hex = password_hash.split('$')
        pwdhash = hashlib.pbkdf2_hmac('sha256',
                                       password.encode('utf-8'),
                                       salt.encode('utf-8'),
                                       100000)
        return pwdhash.hex() == pwdhash_hex
    except:
        return False


def create_token(user_id: int, username: str) -> str:
    """Create a simple JWT-like token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()
    }
    
    # Encode header and payload
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # Create signature
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        # Verify signature
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        expected_signature_encoded = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')
        
        if signature_encoded != expected_signature_encoded:
            return None
        
        # Decode payload
        payload = json.loads(base64.urlsafe_b64decode(payload_encoded + '=='))
        
        # Check expiration
        exp = datetime.fromisoformat(payload['exp'])
        if datetime.utcnow() > exp:
            return None
        
        return payload
    except:
        return None


def get_current_user_id(token: str) -> Optional[int]:
    """Extract user ID from a valid token."""
    payload = verify_token(token)
    if payload:
        return payload.get('user_id')
    return None


# Role-based permissions
ROLE_PERMISSIONS = {
    "owner": {
        "view_board": True,
        "create_quest": True,
        "edit_any_quest": True,
        "delete_any_quest": True,
        "verify_quest": True,
        "manage_members": True,
        "create_invites": True,
        "view_analytics": True
    },
    "organizer": {
        "view_board": True,
        "create_quest": True,
        "edit_own_quest": True,
        "verify_quest": True,
        "create_invites": True,
        "view_analytics": True
    },
    "reviewer": {
        "view_board": True,
        "verify_quest": True,
        "comment_on_quest": True,
        "view_analytics": True
    },
    "friend": {
        "view_board": True,
        "create_quest": True,
        "claim_quest": True,
        "verify_quest": True
    },
    "participant": {
        "view_board": True,
        "claim_quest": True,
        "submit_work": True
    }
}


def generate_invite_token() -> str:
    """Generate a cryptographically secure invite token."""
    return secrets.token_urlsafe(32)


def create_board_invite(
    board_id: str,
    created_by_user_id: int,
    role: str,
    email: Optional[str] = None,
    max_uses: int = 1,
    expires_hours: int = 48
) -> Dict:
    """Create a new board invitation."""
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: {role}")
    
    return {
        "board_id": board_id,
        "created_by_user_id": created_by_user_id,
        "invite_token": generate_invite_token(),
        "email": email,
        "role": role,
        "permissions": ROLE_PERMISSIONS[role],
        "max_uses": max_uses,
        "used_count": 0,
        "expires_at": datetime.utcnow() + timedelta(hours=expires_hours),
        "created_at": datetime.utcnow()
    }


def validate_invite_token(invite: Dict) -> bool:
    """Validate an invite token hasn't expired and hasn't exceeded max uses."""
    if not invite:
        return False
    
    # Check expiration
    if isinstance(invite['expires_at'], str):
        expires_at = datetime.fromisoformat(invite['expires_at'])
    else:
        expires_at = invite['expires_at']
    
    if datetime.utcnow() > expires_at:
        return False
    
    # Check usage
    if invite['used_count'] >= invite['max_uses']:
        return False
    
    return True


def check_permission(permissions: Dict[str, bool], permission: str) -> bool:
    """Check if a set of permissions includes a specific permission."""
    return permissions.get(permission, False)