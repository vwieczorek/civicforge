"""
Tests for token blacklist functionality
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from src.utils.token_blacklist import TokenBlacklist, revoke_token, is_token_revoked, generate_jti


class TestTokenBlacklist:
    """Test cases for TokenBlacklist class"""
    
    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table"""
        table = MagicMock()
        return table
    
    @pytest.fixture
    def token_blacklist(self, mock_table):
        """Create token blacklist with mocked table"""
        with patch('boto3.resource') as mock_resource:
            mock_resource.return_value.Table.return_value = mock_table
            blacklist = TokenBlacklist("test-blacklist")
            blacklist.table = mock_table
            return blacklist
    
    def test_revoke_token_success(self, token_blacklist, mock_table):
        """Test successful token revocation"""
        # Mock successful put_item
        mock_table.put_item.return_value = {}
        
        result = token_blacklist.revoke_token(
            token_jti="test-jti-123",
            user_id="user-456",
            exp_timestamp=1640995200,
            reason="user_logout"
        )
        
        assert result is True
        
        # Verify put_item was called with correct parameters
        put_call = mock_table.put_item.call_args
        item = put_call[1]["Item"]
        
        assert item["jti"] == "test-jti-123"
        assert item["user_id"] == "user-456"
        assert item["reason"] == "user_logout"
        assert item["ttl"] == 1640995200 + 3600  # exp + 1 hour
        assert "revoked_at" in item
    
    def test_revoke_token_failure(self, token_blacklist, mock_table):
        """Test token revocation failure"""
        # Mock DynamoDB error
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable"}},
            "PutItem"
        )
        
        result = token_blacklist.revoke_token(
            token_jti="test-jti-123",
            user_id="user-456",
            exp_timestamp=1640995200
        )
        
        assert result is False
    
    def test_is_token_revoked_true(self, token_blacklist, mock_table):
        """Test checking a revoked token"""
        # Mock response with item (token is revoked)
        mock_table.get_item.return_value = {
            "Item": {
                "jti": "test-jti-123",
                "user_id": "user-456",
                "revoked_at": datetime.utcnow().isoformat()
            }
        }
        
        result = token_blacklist.is_token_revoked("test-jti-123")
        
        assert result is True
        mock_table.get_item.assert_called_once_with(Key={"jti": "test-jti-123"})
    
    def test_is_token_revoked_false(self, token_blacklist, mock_table):
        """Test checking a non-revoked token"""
        # Mock empty response (token not in blacklist)
        mock_table.get_item.return_value = {}
        
        result = token_blacklist.is_token_revoked("test-jti-123")
        
        assert result is False
    
    def test_is_token_revoked_error_fails_closed(self, token_blacklist, mock_table):
        """Test that errors fail closed (treat as revoked)"""
        # Mock DynamoDB error
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable"}},
            "GetItem"
        )
        
        result = token_blacklist.is_token_revoked("test-jti-123")
        
        # Should fail closed - treat as revoked
        assert result is True
    
    @patch('src.utils.token_blacklist.logger')
    def test_revoke_all_user_tokens_not_implemented(self, mock_logger, token_blacklist):
        """Test bulk revocation (currently not implemented)"""
        result = token_blacklist.revoke_all_user_tokens("user-123")
        
        assert result == 0
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        assert "Bulk token revocation requested" in warning_message
        assert "user-123" in warning_message


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('src.utils.token_blacklist.get_token_blacklist')
    def test_revoke_token_convenience(self, mock_get_blacklist):
        """Test revoke_token convenience function"""
        mock_blacklist = MagicMock()
        mock_blacklist.revoke_token.return_value = True
        mock_get_blacklist.return_value = mock_blacklist
        
        result = revoke_token(
            token_jti="test-jti",
            user_id="user-123",
            exp_timestamp=1640995200,
            reason="security_breach"
        )
        
        assert result is True
        mock_blacklist.revoke_token.assert_called_once_with(
            token_jti="test-jti",
            user_id="user-123",
            exp_timestamp=1640995200,
            reason="security_breach"
        )
    
    @patch('src.utils.token_blacklist.get_token_blacklist')
    def test_is_token_revoked_convenience(self, mock_get_blacklist):
        """Test is_token_revoked convenience function"""
        mock_blacklist = MagicMock()
        mock_blacklist.is_token_revoked.return_value = True
        mock_get_blacklist.return_value = mock_blacklist
        
        result = is_token_revoked("test-jti")
        
        assert result is True
        mock_blacklist.is_token_revoked.assert_called_once_with("test-jti")
    
    def test_generate_jti(self):
        """Test JTI generation"""
        jti1 = generate_jti()
        jti2 = generate_jti()
        
        # Should generate valid UUIDs
        assert len(jti1) == 36  # UUID v4 format
        assert '-' in jti1
        
        # Should be unique
        assert jti1 != jti2