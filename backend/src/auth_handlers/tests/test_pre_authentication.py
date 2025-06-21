"""
Tests for Pre-Authentication Lambda Trigger (Rate Limiting)
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from ..pre_authentication import (
    handler, check_rate_limit, record_attempt,
    MAX_ATTEMPTS_PER_HOUR, MAX_ATTEMPTS_PER_DAY, BLOCK_DURATION_MINUTES
)


class TestCheckRateLimit:
    """Test rate limiting logic"""

    def create_mock_table_with_item(self, email_item=None, ip_item=None):
        """Helper to create a mock table with specific items"""
        mock_table = MagicMock()
        
        def get_item_side_effect(Key):
            if Key["identifier"].startswith("email#") and email_item:
                return {"Item": email_item}
            elif Key["identifier"].startswith("ip#") and ip_item:
                return {"Item": ip_item}
            return {}
        
        mock_table.get_item.side_effect = get_item_side_effect
        return mock_table

    def test_allows_first_attempt(self):
        """Test that first attempt is allowed"""
        mock_table = self.create_mock_table_with_item()
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        assert is_allowed is True
        assert reason == "ALLOWED"

    def test_blocks_when_email_blocked(self):
        """Test that blocked emails are rejected"""
        blocked_until = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        mock_table = self.create_mock_table_with_item(
            email_item={
                "identifier": "email#test@example.com",
                "blocked_until": blocked_until,
                "attempts_last_hour": 3
            }
        )
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        assert is_allowed is False
        assert reason == "EMAIL_BLOCKED"

    def test_blocks_hourly_limit_exceeded(self):
        """Test that hourly limit is enforced"""
        mock_table = self.create_mock_table_with_item(
            email_item={
                "identifier": "email#test@example.com",
                "attempts_last_hour": MAX_ATTEMPTS_PER_HOUR,
                "attempts_last_day": MAX_ATTEMPTS_PER_HOUR
            }
        )
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        assert is_allowed is False
        assert reason == "HOURLY_LIMIT_EXCEEDED"
        
        # Verify block was set
        mock_table.update_item.assert_called_once()
        update_args = mock_table.update_item.call_args[1]
        assert "blocked_until" in update_args["UpdateExpression"]

    def test_blocks_daily_limit_exceeded(self):
        """Test that daily limit is enforced"""
        mock_table = self.create_mock_table_with_item(
            email_item={
                "identifier": "email#test@example.com",
                "attempts_last_hour": 2,
                "attempts_last_day": MAX_ATTEMPTS_PER_DAY
            }
        )
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        assert is_allowed is False
        assert reason == "DAILY_LIMIT_EXCEEDED"

    def test_blocks_ip_rate_limit(self):
        """Test that IP-based rate limiting works"""
        mock_table = self.create_mock_table_with_item(
            ip_item={
                "identifier": "ip#192.168.1.1",
                "attempts_last_hour": MAX_ATTEMPTS_PER_HOUR * 2  # Double limit for IPs
            }
        )
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        assert is_allowed is False
        assert reason == "IP_RATE_LIMIT_EXCEEDED"

    def test_handles_no_ip_address(self):
        """Test that missing IP address is handled"""
        mock_table = self.create_mock_table_with_item()
        
        is_allowed, reason = check_rate_limit("test@example.com", "", mock_table)
        
        assert is_allowed is True
        assert reason == "ALLOWED"

    def test_handles_dynamodb_error(self):
        """Test fail-open behavior on DynamoDB errors"""
        mock_table = MagicMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable"}},
            "GetItem"
        )
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        # Should fail open (allow authentication)
        assert is_allowed is True
        assert reason == "RATE_LIMIT_CHECK_FAILED"

    def test_expired_block_is_ignored(self):
        """Test that expired blocks are ignored"""
        blocked_until = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        mock_table = self.create_mock_table_with_item(
            email_item={
                "identifier": "email#test@example.com",
                "blocked_until": blocked_until,
                "attempts_last_hour": 1
            }
        )
        
        is_allowed, reason = check_rate_limit("test@example.com", "192.168.1.1", mock_table)
        
        assert is_allowed is True
        assert reason == "ALLOWED"


class TestRecordAttempt:
    """Test attempt recording"""

    @patch('boto3.resource')
    def test_records_email_attempt(self, mock_boto_resource):
        """Test that email attempts are recorded"""
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        record_attempt("test@example.com", "192.168.1.1", mock_table)
        
        # Should update email counter
        assert mock_table.update_item.call_count >= 1
        
        email_call = mock_table.update_item.call_args_list[0]
        assert email_call[1]["Key"]["identifier"] == "email#test@example.com"
        assert "attempts_last_hour" in email_call[1]["UpdateExpression"]
        assert "attempts_last_day" in email_call[1]["UpdateExpression"]
        assert "ttl" in email_call[1]["UpdateExpression"]

    @patch('boto3.resource')
    def test_records_ip_attempt(self, mock_boto_resource):
        """Test that IP attempts are recorded"""
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        
        record_attempt("test@example.com", "192.168.1.1", mock_table)
        
        # Should update both email and IP counters
        assert mock_table.update_item.call_count == 2
        
        ip_call = mock_table.update_item.call_args_list[1]
        assert ip_call[1]["Key"]["identifier"] == "ip#192.168.1.1"
        assert "attempts_last_hour" in ip_call[1]["UpdateExpression"]

    def test_handles_missing_ip(self):
        """Test that missing IP is handled gracefully"""
        mock_table = MagicMock()
        
        record_attempt("test@example.com", "", mock_table)
        
        # Should only update email counter
        assert mock_table.update_item.call_count == 1

    @patch('logging.Logger.error')
    def test_handles_update_errors(self, mock_logger):
        """Test that update errors are logged"""
        mock_table = MagicMock()
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException"}},
            "UpdateItem"
        )
        
        record_attempt("test@example.com", "192.168.1.1", mock_table)
        
        mock_logger.assert_called_once()
        assert "Failed to record attempt" in mock_logger.call_args[0][0]


class TestHandler:
    """Test the main handler function"""

    @patch('backend.src.auth.pre_authentication.record_attempt')
    @patch('backend.src.auth.pre_authentication.check_rate_limit')
    @patch('boto3.resource')
    def test_allows_valid_attempt(self, mock_boto_resource, mock_check, mock_record):
        """Test that valid attempts are allowed"""
        mock_check.return_value = (True, "ALLOWED")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "requestContext": {
                "sourceIp": "192.168.1.1"
            },
            "response": {}
        }

        with patch.dict(os.environ, {"RATE_LIMIT_TABLE": "test-table"}):
            result = handler(event, None)

        # Should not raise exception
        assert result == event
        
        # Should check rate limit
        mock_check.assert_called_once_with("user@example.com", "192.168.1.1", mock_table)
        
        # Should record attempt
        mock_record.assert_called_once_with("user@example.com", "192.168.1.1", mock_table)

    @patch('backend.src.auth.pre_authentication.check_rate_limit')
    @patch('boto3.resource')
    def test_blocks_rate_limited_attempt(self, mock_boto_resource, mock_check):
        """Test that rate limited attempts are blocked"""
        mock_check.return_value = (False, "HOURLY_LIMIT_EXCEEDED")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "requestContext": {
                "sourceIp": "192.168.1.1"
            },
            "response": {}
        }

        with patch.dict(os.environ, {"RATE_LIMIT_TABLE": "test-table"}):
            with pytest.raises(Exception) as exc_info:
                handler(event, None)

        assert "Authentication rate limit exceeded" in str(exc_info.value)

    def test_skips_rate_limiting_when_flag_set(self):
        """Test that rate limiting can be skipped"""
        event = {
            "request": {
                "skipRateLimit": True,
                "userAttributes": {
                    "email": "admin@example.com"
                }
            },
            "response": {}
        }

        result = handler(event, None)
        
        # Should return without checking rate limits
        assert result == event

    def test_handles_missing_email(self):
        """Test handling of missing email"""
        event = {
            "request": {
                "userAttributes": {}
            },
            "requestContext": {
                "sourceIp": "192.168.1.1"
            },
            "response": {}
        }

        with patch.dict(os.environ, {"RATE_LIMIT_TABLE": "test-table"}):
            # Should still process but with empty email
            result = handler(event, None)
            assert result == event

    def test_handles_missing_ip(self):
        """Test handling of missing IP address"""
        event = {
            "request": {
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "requestContext": {},
            "response": {}
        }

        with patch.dict(os.environ, {"RATE_LIMIT_TABLE": "test-table"}):
            # Should still process with empty IP
            result = handler(event, None)
            assert result == event

    @patch('logging.Logger.warning')
    @patch('backend.src.auth.pre_authentication.check_rate_limit')
    @patch('boto3.resource')
    def test_logs_rate_limit_events(self, mock_boto_resource, mock_check, mock_logger):
        """Test that rate limit events are logged"""
        mock_check.return_value = (False, "EMAIL_BLOCKED")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "requestContext": {
                "sourceIp": "192.168.1.1"
            },
            "response": {}
        }

        with patch.dict(os.environ, {"RATE_LIMIT_TABLE": "test-table"}):
            with pytest.raises(Exception):
                handler(event, None)

        mock_logger.assert_called_once()
        log_message = mock_logger.call_args[0][0]
        assert "Rate limit exceeded" in log_message
        assert "user@example.com" in log_message
        assert "EMAIL_BLOCKED" in log_message

    @patch('logging.Logger.error')
    def test_logs_and_re_raises_errors(self, mock_logger):
        """Test that errors are logged and re-raised"""
        event = {
            "request": {
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch('boto3.resource') as mock_boto:
            mock_boto.side_effect = Exception("DynamoDB error")
            
            with pytest.raises(Exception) as exc_info:
                handler(event, None)

        assert "DynamoDB error" in str(exc_info.value)
        mock_logger.assert_called_once()
        assert "Pre-authentication error" in mock_logger.call_args[0][0]