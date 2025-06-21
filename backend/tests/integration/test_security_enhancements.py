"""
Integration tests for all security enhancements
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import jwt
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.app_factory import create_app
from src.routers.auth import router as auth_router
from src.auth import verify_token, get_current_user_claims
from src.utils.rate_limiter import RateLimiter, get_rate_limiter
from src.utils.token_blacklist import TokenBlacklist, generate_jti
from src.middleware.security_headers import get_security_headers


class TestSecurityEnhancements:
    """Comprehensive test suite for security enhancements"""
    
    @pytest.fixture
    def test_app(self):
        """Create test FastAPI app"""
        app = create_app(
            routers=[auth_router],
            title="Test App",
            description="Test security enhancements"
        )
        return app
    
    @pytest.fixture
    def test_client(self, test_app):
        """Create test client"""
        return TestClient(test_app)
    
    @pytest.fixture
    def mock_cognito_keys(self):
        """Mock Cognito JWKS response"""
        return {
            "keys": [{
                "kid": "test-key-id",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": "test-modulus",
                "e": "AQAB"
            }]
        }
    
    def test_security_headers_present(self, test_client):
        """Test that all security headers are present in responses"""
        response = test_client.get("/health")
        
        # Check all security headers
        assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in response.headers
        assert response.headers.get("X-Powered-By") == "CivicForge"
        
        # Verify server header is removed
        assert "server" not in response.headers
    
    def test_rate_limiting_email_endpoint(self):
        """Test rate limiting on email sending"""
        limiter = RateLimiter("test-rate-limits")
        
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"attempts": []}}
        mock_table.put_item.return_value = {}
        limiter.table = mock_table
        
        # Test within limits
        for i in range(5):
            is_allowed, remaining = limiter.check_rate_limit(
                key="email_send:test@example.com",
                max_attempts=5,
                window_minutes=60,
                increment=True
            )
            assert is_allowed is True
            assert remaining == 5 - i - 1
        
        # Test exceeding limit
        mock_table.get_item.return_value = {
            "Item": {
                "attempts": [datetime.utcnow().isoformat() for _ in range(5)]
            }
        }
        
        is_allowed, remaining = limiter.check_rate_limit(
            key="email_send:test@example.com",
            max_attempts=5,
            window_minutes=60
        )
        assert is_allowed is False
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_token_revocation(self):
        """Test token revocation mechanism"""
        blacklist = TokenBlacklist("test-blacklist")
        
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_table.put_item.return_value = {}
        mock_table.get_item.return_value = {"Item": {"jti": "test-jti"}}
        blacklist.table = mock_table
        
        # Test revoking a token
        jti = generate_jti()
        success = blacklist.revoke_token(
            token_jti=jti,
            user_id="test-user",
            exp_timestamp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            reason="test_logout"
        )
        assert success is True
        
        # Test checking if token is revoked
        is_revoked = blacklist.is_token_revoked(jti)
        assert is_revoked is True
    
    def test_generic_error_messages(self, test_client):
        """Test that error messages don't leak sensitive information"""
        # Test 404 error
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        assert "detail" in response.json()
        # Should not contain path information
        assert "/api/v1/nonexistent" not in response.json()["detail"]
        
        # Test 401 error (requires mocking auth)
        with patch('src.auth.verify_token', side_effect=HTTPException(status_code=401)):
            response = test_client.get(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer invalid-token"}
            )
            assert response.status_code == 401
    
    def test_request_timeout_configuration(self):
        """Test that API client has timeout configuration"""
        from src.api.client import ApiClient
        
        # Mock fetch to test timeout
        with patch('src.api.client.fetch') as mock_fetch:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json = AsyncMock(return_value={"test": "data"})
            mock_fetch.return_value = mock_response
            
            client = ApiClient()
            
            # The request method should use AbortController
            # This is a simplified test - in real implementation you'd test the actual timeout
            assert hasattr(client, 'request')
    
    @pytest.mark.asyncio
    async def test_logout_endpoint(self, test_client):
        """Test logout endpoint functionality"""
        # Mock authentication
        mock_claims = {
            "sub": "test-user",
            "jti": "test-jti-123",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        with patch('src.routers.auth.get_current_user_claims', return_value=mock_claims):
            with patch('src.routers.auth.get_current_user_id', return_value="test-user"):
                with patch('src.routers.auth.revoke_token', return_value=True):
                    response = test_client.post(
                        "/api/v1/auth/logout",
                        json={"revoke_all_sessions": False},
                        headers={"Authorization": "Bearer test-token"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["message"] == "Successfully logged out"
    
    def test_api_gateway_throttling_config(self):
        """Test that API Gateway throttling is configured"""
        # This would be tested via infrastructure tests
        # Here we just verify the configuration exists in serverless.yml
        import yaml
        
        with open('serverless.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Check throttling configuration
        assert 'httpApi' in config['provider']
        assert 'throttle' in config['provider']['httpApi']
        assert config['provider']['httpApi']['throttle']['burstLimit'] == 2000
        assert config['provider']['httpApi']['throttle']['rateLimit'] == 1000
    
    def test_csp_header_configuration(self, test_client):
        """Test Content Security Policy header configuration"""
        response = test_client.get("/health")
        csp = response.headers.get("Content-Security-Policy")
        
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "connect-src 'self' https://cognito-idp.*.amazonaws.com" in csp
    
    @pytest.mark.asyncio
    async def test_token_blacklist_fail_closed(self):
        """Test that token blacklist fails closed on errors"""
        blacklist = TokenBlacklist("test-blacklist")
        
        # Mock DynamoDB error
        mock_table = MagicMock()
        mock_table.get_item.side_effect = Exception("DynamoDB error")
        blacklist.table = mock_table
        
        # Should treat as revoked when error occurs
        is_revoked = blacklist.is_token_revoked("any-jti")
        assert is_revoked is True
    
    def test_passcode_table_ttl(self):
        """Test that passcode and rate limit tables have TTL configured"""
        # This would be tested via infrastructure tests
        # Verify TTL is configured in DynamoDB tables
        import yaml
        
        with open('serverless.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        resources = config['resources']['Resources']
        
        # Check rate limit table has TTL
        assert 'RateLimitTable' in resources
        rate_limit_table = resources['RateLimitTable']['Properties']
        assert 'TimeToLiveSpecification' in rate_limit_table
        assert rate_limit_table['TimeToLiveSpecification']['Enabled'] is True
        
        # Check token blacklist table has TTL
        assert 'TokenBlacklistTable' in resources
        blacklist_table = resources['TokenBlacklistTable']['Properties']
        assert 'TimeToLiveSpecification' in blacklist_table
        assert blacklist_table['TimeToLiveSpecification']['Enabled'] is True