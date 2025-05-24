"""Authentication utilities for CivicForge Board MVP."""

from datetime import datetime, timedelta
from typing import Optional
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