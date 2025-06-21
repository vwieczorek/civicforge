"""
Tests for create_auth_challenge handler with rate limiting
"""

import json
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
import os

# Import the handler directly
from src.auth_handlers.create_auth_challenge import handler, generate_passcode, store_passcode, send_passcode_email


class TestCreateAuthChallengeWithRateLimit:
    """Test create auth challenge handler with rate limiting"""
    
    @pytest.fixture
    def mock_event(self):
        """Create a mock Cognito event"""
        return {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "userAttributes": {
                    "email": "test@example.com"
                }
            },
            "response": {}
        }
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Lambda context"""
        context = MagicMock()
        context.aws_request_id = "test-request-id"
        return context
    
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Set up environment variables"""
        os.environ["PASSCODES_TABLE"] = "test-passcodes-table"
        os.environ["FROM_EMAIL"] = "test@civicforge.org"
        yield
        # Cleanup
        os.environ.pop("PASSCODES_TABLE", None)
        os.environ.pop("FROM_EMAIL", None)
    
    @patch('src.auth_handlers.create_auth_challenge.check_email_rate_limit')
    @patch('src.auth_handlers.create_auth_challenge.dynamodb')
    @patch('src.auth_handlers.create_auth_challenge.ses_client')
    def test_successful_auth_challenge_with_rate_limit(self, mock_ses, mock_dynamodb, mock_rate_limit, mock_event, mock_context):
        """Test successful auth challenge creation with rate limit check"""
        # Mock rate limit check - allowed
        mock_rate_limit.return_value = (True, 4)  # Allowed, 4 attempts remaining
        
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock SES send_email
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        
        # Call handler
        result = handler(mock_event, mock_context)
        
        # Verify rate limit was checked
        mock_rate_limit.assert_called_once_with("test@example.com")
        
        # Verify passcode was stored
        assert mock_table.put_item.called
        put_args = mock_table.put_item.call_args[1]["Item"]
        assert put_args["email"] == "test@example.com"
        assert len(put_args["passcode"]) == 6
        assert put_args["passcode"].isdigit()
        
        # Verify email was sent
        assert mock_ses.send_email.called
        email_args = mock_ses.send_email.call_args[1]
        assert email_args["Source"] == "test@civicforge.org"
        assert email_args["Destination"]["ToAddresses"] == ["test@example.com"]
        
        # Verify response
        assert "publicChallengeParameters" in result["response"]
        assert result["response"]["publicChallengeParameters"]["email"] == "test@example.com"
        assert "privateChallengeParameters" in result["response"]
        assert "passcode" in result["response"]["privateChallengeParameters"]
    
    @patch('src.auth_handlers.create_auth_challenge.check_email_rate_limit')
    @patch('src.auth_handlers.create_auth_challenge.dynamodb')
    def test_rate_limit_exceeded(self, mock_dynamodb, mock_rate_limit, mock_event, mock_context):
        """Test handling when rate limit is exceeded"""
        # Mock rate limit check - exceeded
        mock_rate_limit.return_value = (False, 0)  # Not allowed, 0 attempts remaining
        
        # Call handler
        result = handler(mock_event, mock_context)
        
        # Verify rate limit was checked
        mock_rate_limit.assert_called_once_with("test@example.com")
        
        # Verify no passcode was generated or stored
        assert not mock_dynamodb.Table.return_value.put_item.called
        
        # Verify error response
        assert "publicChallengeParameters" in result["response"]
        assert result["response"]["publicChallengeParameters"]["error"] == "CHALLENGE_CREATION_FAILED"
        assert "privateChallengeParameters" not in result["response"]
    
    @patch('src.auth_handlers.create_auth_challenge.check_email_rate_limit')
    @patch('src.auth_handlers.create_auth_challenge.dynamodb')
    @patch('src.auth_handlers.create_auth_challenge.ses_client')
    def test_email_send_failure_cleanup(self, mock_ses, mock_dynamodb, mock_rate_limit, mock_event, mock_context):
        """Test cleanup when email sending fails"""
        # Mock rate limit check - allowed
        mock_rate_limit.return_value = (True, 3)
        
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock SES send_email failure
        mock_ses.send_email.side_effect = Exception("SES error")
        
        # Call handler
        result = handler(mock_event, mock_context)
        
        # Verify rate limit was checked
        mock_rate_limit.assert_called_once_with("test@example.com")
        
        # Verify passcode was stored initially
        assert mock_table.put_item.called
        
        # Verify cleanup - passcode was deleted
        assert mock_table.delete_item.called
        delete_args = mock_table.delete_item.call_args[1]["Key"]
        assert delete_args["email"] == "test@example.com"
        
        # Verify error response
        assert result["response"]["publicChallengeParameters"]["error"] == "CHALLENGE_CREATION_FAILED"
    
    def test_non_custom_challenge_skip(self, mock_event, mock_context):
        """Test that non-custom challenges are skipped"""
        # Modify event to have different challenge type
        mock_event["request"]["challengeName"] = "PASSWORD_VERIFIER"
        
        with patch('backend.src.auth_handlers.create_auth_challenge.check_email_rate_limit') as mock_rate_limit:
            result = handler(mock_event, mock_context)
            
            # Verify rate limit was NOT checked
            assert not mock_rate_limit.called
            
            # Verify response is unchanged
            assert result == mock_event
    
    @patch('src.auth_handlers.create_auth_challenge.check_email_rate_limit')
    @patch('src.auth_handlers.create_auth_challenge.logger')
    def test_rate_limit_logging(self, mock_logger, mock_rate_limit, mock_event, mock_context):
        """Test proper logging for rate limit events"""
        # Test successful rate limit check
        mock_rate_limit.return_value = (True, 2)
        
        with patch('backend.src.auth_handlers.create_auth_challenge.dynamodb'):
            with patch('backend.src.auth_handlers.create_auth_challenge.ses_client'):
                handler(mock_event, mock_context)
        
        # Verify info log for successful rate limit check
        info_logs = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Rate limit check passed" in log for log in info_logs)
        assert any("Remaining attempts: 2" in log for log in info_logs)
        
        # Reset and test rate limit exceeded
        mock_logger.reset_mock()
        mock_rate_limit.return_value = (False, 0)
        
        handler(mock_event, mock_context)
        
        # Verify warning log for rate limit exceeded
        warning_logs = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("Rate limit exceeded" in log for log in warning_logs)