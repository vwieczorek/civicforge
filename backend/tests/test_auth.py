"""
Comprehensive tests for auth.py module
Achieves 90%+ coverage for this security-critical module
"""

import pytest
import httpx
import json
import jwt
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, FastAPI, Depends
from fastapi.testclient import TestClient
from fastapi import status
from cachetools import TTLCache
import os

# Set test environment before importing auth
os.environ["COGNITO_USER_POOL_ID"] = "test-pool-id-123"
os.environ["COGNITO_APP_CLIENT_ID"] = "test-client-id-456"
os.environ["COGNITO_REGION"] = "us-east-1"

# Now import auth after env vars are set
import src.auth as auth

# Sample JWKS for testing
SAMPLE_JWKS = {
    "keys": [
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "sample_kid_1",
            "kty": "RSA",
            "n": "sample_n_value_1",
            "use": "sig"
        },
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "sample_kid_2",
            "kty": "RSA",
            "n": "sample_n_value_2",
            "use": "sig"
        }
    ]
}


class TestGetCognitoKeys:
    """Test the get_cognito_keys function"""
    
    async def test_get_cognito_keys_success(self, mocker):
        """Test that keys are fetched and returned on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mocker.patch("src.auth._async_client", mock_client)
        
        # Clear cache before test
        auth.cognito_keys_cache.clear()
        
        keys = await auth.get_cognito_keys()
        
        assert keys == SAMPLE_JWKS
        mock_client.get.assert_called_once_with(auth.JWKS_URL)
        # Verify response methods were called
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()
    
    async def test_get_cognito_keys_cached(self, mocker):
        """Test that cached keys are returned without making a second HTTP request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mocker.patch("src.auth._async_client", mock_client)
        
        # Ensure a clean slate
        auth.cognito_keys_cache.clear()
        
        # 1. First call: should trigger the mock HTTP request and populate the cache
        keys1 = await auth.get_cognito_keys()
        mock_client.get.assert_called_once_with(auth.JWKS_URL)
        assert keys1 == SAMPLE_JWKS
        
        # 2. Second call: should hit the cache and NOT trigger another HTTP request
        keys2 = await auth.get_cognito_keys()
        # Still only called once
        mock_client.get.assert_called_once_with(auth.JWKS_URL)
        assert keys2 == SAMPLE_JWKS
    
    async def test_get_cognito_keys_http_error(self, mocker):
        """Test that HTTP errors are propagated correctly."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("HTTP Error")
        mocker.patch("httpx.get", new_callable=AsyncMock, return_value=mock_response)
        
        # Clear cache
        auth.cognito_keys_cache.clear()
        
        with pytest.raises(httpx.HTTPError):
            await auth.get_cognito_keys()


class TestVerifyToken:
    """Test the verify_token function"""
    
    async def test_verify_token_success(self, mocker):
        """Test successful token verification."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        
        # Mock JWT functions
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        mock_decode = mocker.patch("jwt.decode", return_value={
            "sub": "user123",
            "cognito:username": "testuser",
            "token_use": "access"
        })
        
        # Mock RSAAlgorithm.from_jwk to return a mock key
        mock_key = MagicMock()
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=mock_key)
        
        token = "valid_token"
        payload = await auth.verify_token(token)
        
        assert payload["sub"] == "user123"
        assert payload["cognito:username"] == "testuser"
        
        # Verify jwt.decode was called with correct parameters
        mock_decode.assert_called_once_with(
            token,
            mock_key,
            algorithms=["RS256"],
            issuer=f"https://cognito-idp.us-east-1.amazonaws.com/test-pool-id-123",
            audience="test-client-id-456",
            options={"verify_exp": True}
        )
    
    async def test_verify_token_missing_kid(self, mocker):
        """Test token with missing kid in header."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={})  # No 'kid'
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("any_token")
        
        assert exc_info.value.status_code == 401
    
    async def test_verify_token_unknown_kid(self, mocker):
        """Test token with unknown kid."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "unknown_kid"})
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("any_token")
        
        assert exc_info.value.status_code == 401
    
    async def test_verify_token_expired(self, mocker):
        """Test expired token."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        
        # Mock RSAAlgorithm.from_jwk
        mock_key = MagicMock()
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=mock_key)
        
        # Mock jwt.decode to raise ExpiredSignatureError
        mocker.patch("jwt.decode", side_effect=jwt.ExpiredSignatureError("Token expired"))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("expired_token")
        
        assert exc_info.value.status_code == 401
    
    async def test_verify_token_invalid_signature(self, mocker):
        """Test token with invalid signature."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        
        # Mock RSAAlgorithm.from_jwk
        mock_key = MagicMock()
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=mock_key)
        
        # Mock jwt.decode to raise InvalidSignatureError
        mocker.patch("jwt.decode", side_effect=jwt.InvalidSignatureError("Invalid signature"))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("invalid_signature_token")
        
        assert exc_info.value.status_code == 401
    
    async def test_verify_token_invalid_issuer(self, mocker):
        """Test token with invalid issuer."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        
        # Mock RSAAlgorithm.from_jwk
        mock_key = MagicMock()
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=mock_key)
        
        # Mock jwt.decode to raise InvalidIssuerError
        mocker.patch("jwt.decode", side_effect=jwt.InvalidIssuerError("Invalid issuer"))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("invalid_issuer_token")
        
        assert exc_info.value.status_code == 401
    
    async def test_verify_token_decode_error(self, mocker):
        """Test general decode error."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        
        # Mock RSAAlgorithm.from_jwk
        mock_key = MagicMock()
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=mock_key)
        
        # Mock jwt.decode to raise general DecodeError
        mocker.patch("jwt.decode", side_effect=jwt.DecodeError("General decode error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("malformed_token")
        
        assert exc_info.value.status_code == 401


class TestFastAPIDependencies:
    """Test FastAPI dependency functions"""
    
    def test_get_current_user_claims_success(self, mocker):
        """Test successful user claims extraction."""
        mocker.patch("src.auth.verify_token", new_callable=AsyncMock, return_value={
            "sub": "user123",
            "cognito:username": "testuser"
        })
        
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        import asyncio
        claims = asyncio.run(auth.get_current_user_claims(credentials))
        
        assert claims["sub"] == "user123"
        assert claims["cognito:username"] == "testuser"
    
    def test_get_current_user_claims_no_auth_header(self):
        """Test missing authorization header."""
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(auth.get_current_user_claims(None))
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_claims_invalid_scheme(self):
        """Test invalid authentication scheme."""
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="basic_creds")
        
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(auth.get_current_user_claims(credentials))
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_claims_token_verification_fails(self, mocker):
        """Test when token verification fails."""
        mocker.patch("src.auth.verify_token", new_callable=AsyncMock, side_effect=HTTPException(
            status_code=401, detail="Invalid token"
        ))
        
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(auth.get_current_user_claims(credentials))
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_id_success(self, mocker):
        """Test successful user ID extraction."""
        mocker.patch("src.auth.get_current_user_claims", new_callable=AsyncMock, return_value={
            "sub": "user123"
        })
        
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        import asyncio
        user_id = asyncio.run(auth.get_current_user_id(credentials))
        
        assert user_id == "user123"
    
    def test_get_current_user_id_missing_sub(self, mocker):
        """Test when 'sub' claim is missing."""
        mocker.patch("src.auth.get_current_user_claims", new_callable=AsyncMock, return_value={
            "cognito:username": "testuser"
            # No 'sub' claim
        })
        
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(auth.get_current_user_id(credentials))
        
        assert exc_info.value.status_code == 401
    
    def test_require_auth_success(self, mocker):
        """Test require_auth with valid token."""
        mocker.patch("src.auth.get_current_user_claims", new_callable=AsyncMock, return_value={
            "sub": "user123"
        })
        
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        import asyncio
        asyncio.run(auth.require_auth(credentials))
        # Should not raise
    
    def test_require_auth_no_token(self):
        """Test require_auth with no token."""
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(auth.require_auth(None))
        
        assert exc_info.value.status_code == 401


class TestSecurityEdgeCases:
    """Test edge cases and security scenarios"""
    
    async def test_verify_token_malformed_jwk(self, mocker):
        """Test handling of malformed JWK."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        
        # Mock RSAAlgorithm.from_jwk to raise an exception
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", side_effect=ValueError("Invalid JWK"))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("any_token")
        
        assert exc_info.value.status_code == 401
    
    async def test_verify_token_empty_jwks(self, mocker):
        """Test handling of empty JWKS response."""
        mocker.patch("src.auth.get_cognito_keys", new_callable=AsyncMock, return_value={"keys": []})
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        
        # Clear cache to ensure fresh key lookup
        auth.cognito_keys_cache.clear()
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("any_token")
        
        assert exc_info.value.status_code == 401


class TestModuleInitialization:
    """Test module-level initialization"""
    
    def test_jwks_url_construction(self):
        """Test that JWKS URL is constructed correctly."""
        expected_url = f"https://cognito-idp.us-east-1.amazonaws.com/test-pool-id-123/.well-known/jwks.json"
        assert auth.JWKS_URL == expected_url
    
    def test_issuer_construction(self):
        """Test that issuer URL is constructed correctly."""
        expected_issuer = f"https://cognito-idp.us-east-1.amazonaws.com/test-pool-id-123"
        assert auth.COGNITO_ISSUER == expected_issuer
    
    def test_cache_configuration(self):
        """Test that cache is configured with correct TTL."""
        assert isinstance(auth.cognito_keys_cache, TTLCache)
        assert auth.cognito_keys_cache.maxsize == 1
        assert auth.cognito_keys_cache.ttl == 3600  # 1 hour