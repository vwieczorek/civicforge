"""
JWT authentication with AWS Cognito
"""

import os
import json
import logging
from typing import Dict
import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from cachetools import TTLCache

# Configure logger
logger = logging.getLogger(__name__)

# Import security metrics
try:
    from .utils.security_metrics import (
        record_authentication_failure,
        record_invalid_token_attempt,
    )
except ImportError:
    # Fallback if metrics not available
    def record_authentication_failure(user_id=None, reason="unknown"):
        logger.warning(f"Auth failure: {reason}, user: {user_id}")

    def record_invalid_token_attempt(token_type="unknown", error=None):
        logger.warning(f"Invalid token: {token_type}, error: {error}")

# Import token blacklist
try:
    from .utils.token_blacklist import is_token_revoked
except ImportError:
    # Fallback if blacklist not available
    def is_token_revoked(jti: str) -> bool:
        logger.warning("Token blacklist not available, skipping revocation check")
        return False


# Configuration
COGNITO_REGION = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID")
COGNITO_API_AUDIENCE = os.environ.get("COGNITO_API_AUDIENCE")

# Validate required environment variables at startup
if not COGNITO_USER_POOL_ID:
    raise ValueError("Missing required environment variable: COGNITO_USER_POOL_ID")
if not COGNITO_APP_CLIENT_ID:
    raise ValueError("Missing required environment variable: COGNITO_APP_CLIENT_ID")

# JWT validation
COGNITO_ISSUER = (
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
)
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

# Security scheme
security = HTTPBearer()

# Cache keys for 1 hour to handle key rotation
cognito_keys_cache = TTLCache(maxsize=1, ttl=3600)

# Create an async HTTP client with timeout
_async_client = httpx.AsyncClient(timeout=5.0)


async def get_cognito_keys() -> Dict:
    """Fetch and cache Cognito public keys with TTL"""
    # Manual caching for async function
    cache_key = "cognito_keys"

    # Check if keys are in cache
    if cache_key in cognito_keys_cache:
        return cognito_keys_cache[cache_key]

    # Fetch keys if not in cache
    response = await _async_client.get(JWKS_URL)
    response.raise_for_status()
    keys = response.json()

    # Store in cache
    cognito_keys_cache[cache_key] = keys
    return keys


async def verify_token(token: str, expected_token_use: str = "access") -> Dict:
    """Verify and decode a Cognito JWT token"""
    try:
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )

        # Get the public key with retry mechanism
        keys = await get_cognito_keys()
        key = None
        for k in keys["keys"]:
            if k["kid"] == kid:
                key = k
                break

        if not key:
            # Try refreshing the keys cache in case of key rotation
            cognito_keys_cache.clear()
            keys = await get_cognito_keys()
            for k in keys["keys"]:
                if k["kid"] == kid:
                    key = k
                    break

            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed",
                )

        # Construct the public key
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))

        # Verify and decode the token
        # ID tokens have 'aud' (audience) which is the App Client ID.
        # Access tokens from a User Pool with a Resource Server have an 'aud' claim.
        # Legacy access tokens (without a resource server) have 'client_id' instead of 'aud'.
        decode_options = {"verify_exp": True}
        audience_to_check = None

        if expected_token_use == "access":
            if COGNITO_API_AUDIENCE:
                # New method: Validate 'aud' claim against the API audience
                audience_to_check = COGNITO_API_AUDIENCE
                decode_options["verify_aud"] = True
            # else: Legacy method, check 'client_id' manually after decoding
        elif expected_token_use == "id":
            # ID tokens always have audience validated against the App Client ID
            audience_to_check = COGNITO_APP_CLIENT_ID
            decode_options["verify_aud"] = True

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=COGNITO_ISSUER,
            audience=audience_to_check,
            options=decode_options,
        )

        # For legacy access tokens (no API audience configured), manually verify the client_id
        if expected_token_use == "access" and not COGNITO_API_AUDIENCE:
            client_id = payload.get("client_id")
            if client_id != COGNITO_APP_CLIENT_ID:
                raise jwt.InvalidTokenError("Invalid client_id")

        # Validate token_use claim
        token_use = payload.get("token_use")
        if token_use != expected_token_use:
            record_invalid_token_attempt(
                token_type="jwt", error=f"wrong_token_use:{token_use}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )

        # Check if token is revoked (if JTI is present)
        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            record_invalid_token_attempt(
                token_type="jwt", error="token_revoked"
            )
            logger.warning(f"Revoked token used: jti={jti}, sub={payload.get('sub')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )

        return payload

    except jwt.ExpiredSignatureError:
        record_invalid_token_attempt(token_type="jwt", error="expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
    except jwt.InvalidTokenError as e:
        record_invalid_token_attempt(token_type="jwt", error=str(type(e).__name__))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
    except Exception as e:
        # Log the actual error for debugging purposes
        logger.error(
            f"An unexpected error occurred during token verification: {e}",
            exc_info=True,
        )
        record_authentication_failure(reason="unexpected_error")
        # Catch any other exceptions to prevent information leakage
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


async def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict:
    """Get the current user's claims from the JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
    token = credentials.credentials
    
    # Try access token first, then fall back to ID token
    # This is a temporary measure during the migration
    try:
        # Try as access token first
        return await verify_token(token, expected_token_use="access")
    except HTTPException:
        # If that fails, try as ID token (backward compatibility)
        try:
            logger.warning("Access token validation failed, falling back to ID token")
            return await verify_token(token, expected_token_use="id")
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Get the current user's ID (Cognito sub)"""
    claims = await get_current_user_claims(credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
    return user_id


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict:
    """Require authentication for an endpoint"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
    return await get_current_user_claims(credentials)
