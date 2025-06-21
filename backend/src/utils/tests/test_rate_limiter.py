"""
Tests for rate limiting functionality
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from src.utils.rate_limiter import RateLimiter, check_email_rate_limit, check_auth_rate_limit


class TestRateLimiter:
    """Test cases for RateLimiter class"""
    
    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table"""
        table = MagicMock()
        return table
    
    @pytest.fixture
    def rate_limiter(self, mock_table):
        """Create rate limiter with mocked table"""
        with patch('boto3.resource') as mock_resource:
            mock_resource.return_value.Table.return_value = mock_table
            limiter = RateLimiter("test-table")
            limiter.table = mock_table
            return limiter
    
    def test_check_rate_limit_no_previous_attempts(self, rate_limiter, mock_table):
        """Test rate limit check with no previous attempts"""
        # Mock empty response
        mock_table.get_item.return_value = {"Item": {}}
        
        is_allowed, remaining = rate_limiter.check_rate_limit(
            key="test:key",
            max_attempts=5,
            window_minutes=60,
            increment=True
        )
        
        assert is_allowed is True
        assert remaining == 4  # 5 - 1 (current attempt)
        
        # Verify put_item was called
        assert mock_table.put_item.called
        put_call = mock_table.put_item.call_args
        assert put_call[1]["Item"]["key"] == "test:key"
        assert len(put_call[1]["Item"]["attempts"]) == 1
    
    def test_check_rate_limit_with_previous_attempts(self, rate_limiter, mock_table):
        """Test rate limit check with existing attempts"""
        current_time = datetime.utcnow()
        recent_time = (current_time - timedelta(minutes=30)).isoformat()
        old_time = (current_time - timedelta(minutes=90)).isoformat()
        
        # Mock response with mixed old and recent attempts
        mock_table.get_item.return_value = {
            "Item": {
                "attempts": [old_time, recent_time]
            }
        }
        
        is_allowed, remaining = rate_limiter.check_rate_limit(
            key="test:key",
            max_attempts=3,
            window_minutes=60,
            increment=True
        )
        
        assert is_allowed is True
        assert remaining == 1  # 3 - 1 (recent) - 1 (current)
        
        # Verify old attempts were filtered out
        put_call = mock_table.put_item.call_args
        attempts = put_call[1]["Item"]["attempts"]
        assert len(attempts) == 2  # recent + current
        assert old_time not in attempts
    
    def test_check_rate_limit_exceeded(self, rate_limiter, mock_table):
        """Test rate limit when limit is exceeded"""
        current_time = datetime.utcnow()
        recent_attempts = [
            (current_time - timedelta(minutes=i)).isoformat()
            for i in range(5)
        ]
        
        mock_table.get_item.return_value = {
            "Item": {"attempts": recent_attempts}
        }
        
        is_allowed, remaining = rate_limiter.check_rate_limit(
            key="test:key",
            max_attempts=5,
            window_minutes=60,
            increment=True
        )
        
        assert is_allowed is False
        assert remaining == 0
        
        # Verify put_item was NOT called when limit exceeded
        assert not mock_table.put_item.called
    
    def test_check_rate_limit_no_increment(self, rate_limiter, mock_table):
        """Test rate limit check without incrementing counter"""
        mock_table.get_item.return_value = {"Item": {"attempts": []}}
        
        is_allowed, remaining = rate_limiter.check_rate_limit(
            key="test:key",
            max_attempts=5,
            window_minutes=60,
            increment=False
        )
        
        assert is_allowed is True
        assert remaining == 5
        
        # Verify put_item was NOT called
        assert not mock_table.put_item.called
    
    def test_check_rate_limit_dynamodb_error(self, rate_limiter, mock_table):
        """Test rate limit fails open on DynamoDB error"""
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable"}},
            "GetItem"
        )
        
        is_allowed, remaining = rate_limiter.check_rate_limit(
            key="test:key",
            max_attempts=5,
            window_minutes=60
        )
        
        # Should fail open (allow request)
        assert is_allowed is True
        assert remaining is None
    
    def test_reset_rate_limit(self, rate_limiter, mock_table):
        """Test resetting rate limit"""
        mock_table.delete_item.return_value = {}
        
        result = rate_limiter.reset_rate_limit("test:key")
        
        assert result is True
        mock_table.delete_item.assert_called_once_with(Key={"key": "test:key"})
    
    def test_reset_rate_limit_error(self, rate_limiter, mock_table):
        """Test reset rate limit with error"""
        mock_table.delete_item.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable"}},
            "DeleteItem"
        )
        
        result = rate_limiter.reset_rate_limit("test:key")
        
        assert result is False


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('src.utils.rate_limiter.get_rate_limiter')
    def test_check_email_rate_limit(self, mock_get_limiter):
        """Test email rate limit convenience function"""
        mock_limiter = MagicMock()
        mock_limiter.check_rate_limit.return_value = (True, 3)
        mock_get_limiter.return_value = mock_limiter
        
        is_allowed, remaining = check_email_rate_limit("test@example.com")
        
        assert is_allowed is True
        assert remaining == 3
        
        mock_limiter.check_rate_limit.assert_called_once_with(
            key="email_send:test@example.com",
            max_attempts=5,
            window_minutes=60,
            increment=True
        )
    
    @patch('src.utils.rate_limiter.get_rate_limiter')
    def test_check_auth_rate_limit(self, mock_get_limiter):
        """Test authentication rate limit convenience function"""
        mock_limiter = MagicMock()
        mock_limiter.check_rate_limit.return_value = (False, 0)
        mock_get_limiter.return_value = mock_limiter
        
        is_allowed, remaining = check_auth_rate_limit("192.168.1.1")
        
        assert is_allowed is False
        assert remaining == 0
        
        mock_limiter.check_rate_limit.assert_called_once_with(
            key="auth_attempt:192.168.1.1",
            max_attempts=10,
            window_minutes=15,
            increment=True
        )