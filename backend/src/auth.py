"""
JWT authentication with AWS Cognito
"""

import os
import json
from typing import Dict
import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from cachetools import cached, TTLCache

# Configuration
COGNITO_REGION = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID")

# Validate required environment variables at startup
if not COGNITO_USER_POOL_ID:
    raise ValueError("Missing required environment variable: COGNITO_USER_POOL_ID")
if not COGNITO_APP_CLIENT_ID:
    raise ValueError("Missing required environment variable: COGNITO_APP_CLIENT_ID")

# JWT validation
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

# Security scheme
security = HTTPBearer()

# Cache keys for 1 hour to handle key rotation
cognito_keys_cache = TTLCache(maxsize=1, ttl=3600)


@cached(cognito_keys_cache)
def get_cognito_keys() -> Dict:
    """Fetch and cache Cognito public keys with TTL"""
    response = httpx.get(JWKS_URL)
    response.raise_for_status()
    return response.json()


async def verify_token(token: str, expected_token_use: str = "id") -> Dict:
    """Verify and decode a Cognito JWT token"""
    try:
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
        
        # Get the public key with retry mechanism
        keys = get_cognito_keys()
        key = None
        for k in keys["keys"]:
            if k["kid"] == kid:
                key = k
                break
        
        if not key:
            # Try refreshing the keys cache in case of key rotation
            cognito_keys_cache.clear()
            keys = get_cognito_keys()
            for k in keys["keys"]:
                if k["kid"] == kid:
                    key = k
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
        
        # Construct the public key
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=COGNITO_ISSUER,
            audience=COGNITO_APP_CLIENT_ID,
            options={"verify_exp": True}
        )
        
        # Validate token_use claim
        token_use = payload.get("token_use")
        if token_use != expected_token_use:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    except Exception:
        # Catch any other exceptions to prevent information leakage
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """Get the current user's claims from the JWT token"""
    token = credentials.credentials
    return await verify_token(token)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Get the current user's ID (Cognito sub)"""
    claims = await get_current_user_claims(credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    return user_id


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """Require authentication for an endpoint"""
    return await get_current_user_claims(credentials)