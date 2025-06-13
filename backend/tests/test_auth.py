"""
Comprehensive tests for auth.py module
Achieves 90%+ coverage for this security-critical module
"""

import pytest
import httpx
import json
import jwt
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, FastAPI, Depends
from fastapi.testclient import TestClient
from fastapi import status
from cachetools import TTLCache
import os

# Set test environment before importing auth
os.environ["COGNITO_USER_POOL_ID"] = "test-pool-id-123"
os.environ["COGNITO_APP_CLIENT_ID"] = "test-client-id-456"
os.environ["COGNITO_REGION"] = "us-east-1"

from src import auth
from src.auth import get_current_user_id, get_current_user_claims, require_auth

# Sample JWKS response from Cognito
SAMPLE_JWKS = {
    "keys": [
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "sample_kid_1",
            "kty": "RSA",
            "n": "xjFV8wWI7p3LbdWJPCvCxWlgPkE7_MkgIA",
            "use": "sig",
        },
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "sample_kid_2",
            "kty": "RSA",
            "n": "yKLM9nOP1qR2sTUVWXvZ8aB9cDEfGhI",
            "use": "sig",
        }
    ]
}


class TestGetCognitoKeys:
    """Test the get_cognito_keys function"""
    
    def test_get_cognito_keys_success(self, mocker):
        """Test that keys are fetched and returned on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_get = mocker.patch("httpx.get", return_value=mock_response)
        
        # Clear cache before test
        auth.cognito_keys_cache.clear()
        
        keys = auth.get_cognito_keys()
        
        assert keys == SAMPLE_JWKS
        mock_get.assert_called_once_with(auth.JWKS_URL)
        # Verify response methods were called
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()
    
    def test_get_cognito_keys_cached(self, mocker):
        """Test that cached keys are returned without making a second HTTP request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_get = mocker.patch("httpx.get", return_value=mock_response)
        
        # Ensure a clean slate
        auth.cognito_keys_cache.clear()
        
        # 1. First call: should trigger the mock HTTP request and populate the cache
        keys1 = auth.get_cognito_keys()
        mock_get.assert_called_once_with(auth.JWKS_URL)
        assert keys1 == SAMPLE_JWKS
        
        # 2. Second call: should hit the cache and NOT trigger another HTTP request
        keys2 = auth.get_cognito_keys()
        mock_get.assert_called_once()  # Assert it's still just one call
        assert keys2 == SAMPLE_JWKS
    
    def test_get_cognito_keys_http_error(self, mocker):
        """Test that an exception is raised on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", 
            request=MagicMock(), 
            response=MagicMock(status_code=404)
        )
        mocker.patch("httpx.get", return_value=mock_response)
        
        # Clear cache before test
        auth.cognito_keys_cache.clear()
        
        with pytest.raises(httpx.HTTPStatusError):
            auth.get_cognito_keys()


class TestVerifyToken:
    """Test the verify_token function"""
    
    def test_verify_token_success(self, mocker):
        """Test successful token verification."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        
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
        payload = auth.verify_token(token)
        
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
    
    def test_verify_token_missing_kid(self, mocker):
        """Test token with missing kid in header."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={})  # No 'kid'
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("any_token")
        
        assert exc_info.value.status_code == 401
        assert "Key ID (kid) not found in token header" in exc_info.value.detail
    
    def test_verify_token_unknown_kid(self, mocker):
        """Test token with a KID that is not in the JWKS."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "unknown_kid"})
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("any_token")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Public key not found"
    
    def test_verify_token_expired(self, mocker):
        """Test expired token handling."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=MagicMock())
        mocker.patch("jwt.decode", side_effect=jwt.ExpiredSignatureError())
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("expired_token")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token has expired"
    
    def test_verify_token_invalid_signature(self, mocker):
        """Test invalid signature handling."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=MagicMock())
        mocker.patch("jwt.decode", side_effect=jwt.InvalidSignatureError())
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("invalid_signature_token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    def test_verify_token_invalid_issuer(self, mocker):
        """Test invalid issuer handling."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=MagicMock())
        mocker.patch("jwt.decode", side_effect=jwt.InvalidIssuerError())
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("invalid_issuer_token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    def test_verify_token_decode_error(self, mocker):
        """Test general decode error handling."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        mocker.patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=MagicMock())
        mocker.patch("jwt.decode", side_effect=jwt.DecodeError("Malformed token"))
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("malformed_token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


class TestFastAPIDependencies:
    """Test FastAPI dependencies using TestClient"""
    
    @pytest.fixture
    def test_app(self):
        """Create a minimal FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/user/claims")
        async def get_claims_endpoint(claims = Depends(get_current_user_claims)):
            return claims
        
        @app.get("/user/id")
        async def get_user_id_endpoint(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
        
        @app.get("/protected")
        async def protected_endpoint(auth = Depends(require_auth)):
            return {"message": "Access granted"}
        
        return app
    
    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)
    
    def test_get_current_user_claims_success(self, client, mocker):
        """Test get_current_user_claims with valid token."""
        mock_payload = {
            "sub": "user-abc-123",
            "cognito:username": "testuser",
            "token_use": "access"
        }
        mocker.patch("src.auth.verify_token", return_value=mock_payload)
        
        response = client.get(
            "/user/claims", 
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        assert response.json() == mock_payload
    
    def test_get_current_user_claims_no_auth_header(self, client):
        """Test missing Authorization header."""
        response = client.get("/user/claims")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"
    
    def test_get_current_user_claims_invalid_scheme(self, client):
        """Test invalid authorization scheme (not Bearer)."""
        response = client.get(
            "/user/claims",
            headers={"Authorization": "Basic dXNlcjpwYXNz"}  # Basic auth instead of Bearer
        )
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid authentication credentials"
    
    def test_get_current_user_claims_token_verification_fails(self, client, mocker):
        """Test when token verification fails."""
        mocker.patch(
            "src.auth.verify_token", 
            side_effect=HTTPException(status_code=401, detail="Token expired")
        )
        
        response = client.get(
            "/user/claims",
            headers={"Authorization": "Bearer expired-token"}
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Token expired"
    
    def test_get_current_user_id_success(self, client, mocker):
        """Test get_current_user_id with valid token containing sub."""
        mocker.patch("src.auth.verify_token", return_value={
            "sub": "user-xyz-789",
            "cognito:username": "testuser2"
        })
        
        response = client.get(
            "/user/id",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"user_id": "user-xyz-789"}
    
    def test_get_current_user_id_missing_sub(self, client, mocker):
        """Test get_current_user_id when sub claim is missing."""
        # Mock token payload without 'sub' claim
        mocker.patch("src.auth.verify_token", return_value={
            "cognito:username": "testuser",
            "token_use": "access"
        })
        
        response = client.get(
            "/user/id",
            headers={"Authorization": "Bearer token-without-sub"}
        )
        
        # After fix, it should return 401
        assert response.status_code == 401
        assert "not found in token" in response.json()["detail"]
    
    def test_require_auth_success(self, client, mocker):
        """Test require_auth dependency allows access with valid token."""
        mocker.patch("src.auth.verify_token", return_value={
            "sub": "user-123",
            "token_use": "access"
        })
        
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"message": "Access granted"}
    
    def test_require_auth_no_token(self, client):
        """Test require_auth dependency blocks access without token."""
        response = client.get("/protected")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"


class TestSecurityEdgeCases:
    """Test security edge cases and malformed inputs"""
    
    def test_verify_token_malformed_jwk(self, mocker):
        """Test handling of malformed JWK data."""
        mocker.patch("src.auth.get_cognito_keys", return_value=SAMPLE_JWKS)
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "sample_kid_1"})
        mocker.patch(
            "jwt.algorithms.RSAAlgorithm.from_jwk",
            side_effect=ValueError("Invalid key data")
        )
        
        with pytest.raises(ValueError):
            auth.verify_token("token")
    
    def test_verify_token_empty_jwks(self, mocker):
        """Test handling when JWKS endpoint returns empty keys."""
        mocker.patch("src.auth.get_cognito_keys", return_value={"keys": []})
        mocker.patch("jwt.get_unverified_header", return_value={"kid": "any_kid"})
        
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("token")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Public key not found"


class TestModuleInitialization:
    """Test module initialization and configuration"""
    
    def test_jwks_url_construction(self):
        """Test that JWKS URL is constructed correctly."""
        expected_url = (
            "https://cognito-idp.us-east-1.amazonaws.com/"
            "test-pool-id-123/.well-known/jwks.json"
        )
        assert auth.JWKS_URL == expected_url
    
    def test_issuer_construction(self):
        """Test that issuer URL is constructed correctly."""
        expected_issuer = (
            "https://cognito-idp.us-east-1.amazonaws.com/test-pool-id-123"
        )
        assert auth.COGNITO_ISSUER == expected_issuer
    
    def test_cache_configuration(self):
        """Test that TTL cache is configured correctly."""
        assert isinstance(auth.cognito_keys_cache, TTLCache)
        assert auth.cognito_keys_cache.maxsize == 1  # Only one JWKS URL to cache
        assert auth.cognito_keys_cache.ttl == 3600  # 1 hour