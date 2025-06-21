"""
Tests for Verify Auth Challenge Response Lambda Trigger
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import ClientError
from ..verify_auth_challenge import (
    handler, verify_passcode, record_security_event, MAX_ATTEMPTS
)


class TestVerifyPasscode:
    """Test passcode verification logic"""

    def create_mock_table_with_item(self, item):
        """Helper to create a mock table with a specific item"""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": item}
        return mock_table

    def test_valid_passcode_verification(self):
        """Test successful passcode verification"""
        mock_table = self.create_mock_table_with_item({
            "email": "test@example.com",
            "passcode": "123456",
            "attempts": 0,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        })

        is_valid, reason = verify_passcode("test@example.com", "123456", mock_table)

        assert is_valid is True
        assert reason == "VALID"
        
        # Verify passcode was deleted after successful verification
        mock_table.delete_item.assert_called_once_with(
            Key={"email": "test@example.com"}
        )

    def test_invalid_passcode(self):
        """Test invalid passcode increments attempts"""
        mock_table = self.create_mock_table_with_item({
            "email": "test@example.com",
            "passcode": "123456",
            "attempts": 0,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        })

        is_valid, reason = verify_passcode("test@example.com", "999999", mock_table)

        assert is_valid is False
        assert reason == "INVALID_PASSCODE"
        
        # Verify attempts were incremented
        mock_table.update_item.assert_called_once()
        update_args = mock_table.update_item.call_args[1]
        assert update_args["UpdateExpression"] == "SET attempts = attempts + :inc"
        assert update_args["ExpressionAttributeValues"][":inc"] == 1

    def test_no_passcode_found(self):
        """Test when no passcode exists for email"""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item key

        is_valid, reason = verify_passcode("test@example.com", "123456", mock_table)

        assert is_valid is False
        assert reason == "NO_PASSCODE_FOUND"

    def test_expired_passcode(self):
        """Test expired passcode is rejected"""
        mock_table = self.create_mock_table_with_item({
            "email": "test@example.com",
            "passcode": "123456",
            "attempts": 0,
            "expires_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        })

        is_valid, reason = verify_passcode("test@example.com", "123456", mock_table)

        assert is_valid is False
        assert reason == "PASSCODE_EXPIRED"
        
        # Verify expired passcode was deleted
        mock_table.delete_item.assert_called_once_with(
            Key={"email": "test@example.com"}
        )

    def test_max_attempts_exceeded(self):
        """Test max attempts blocks verification"""
        mock_table = self.create_mock_table_with_item({
            "email": "test@example.com",
            "passcode": "123456",
            "attempts": MAX_ATTEMPTS,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        })

        is_valid, reason = verify_passcode("test@example.com", "123456", mock_table)

        assert is_valid is False
        assert reason == "MAX_ATTEMPTS_EXCEEDED"
        
        # Verify passcode was deleted after max attempts
        mock_table.delete_item.assert_called_once_with(
            Key={"email": "test@example.com"}
        )

    def test_dynamodb_error_handling(self):
        """Test handling of DynamoDB errors"""
        mock_table = MagicMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "GetItem"
        )

        is_valid, reason = verify_passcode("test@example.com", "123456", mock_table)

        assert is_valid is False
        assert reason == "VERIFICATION_ERROR"

    def test_unexpected_error_handling(self):
        """Test handling of unexpected errors"""
        mock_table = MagicMock()
        mock_table.get_item.side_effect = Exception("Unexpected error")

        is_valid, reason = verify_passcode("test@example.com", "123456", mock_table)

        assert is_valid is False
        assert reason == "VERIFICATION_ERROR"


class TestRecordSecurityEvent:
    """Test security event recording"""

    @patch('logging.Logger.info')
    def test_records_security_event(self, mock_logger):
        """Test that security events are logged properly"""
        record_security_event(
            email="test@example.com",
            event_type="EMAIL_PASSCODE",
            success=True,
            reason="VALID"
        )

        mock_logger.assert_called_once()
        logged_data = json.loads(mock_logger.call_args[0][0])
        
        assert logged_data["event_type"] == "AUTH_VERIFICATION"
        assert logged_data["email"] == "test@example.com"
        assert logged_data["verification_type"] == "EMAIL_PASSCODE"
        assert logged_data["success"] is True
        assert logged_data["reason"] == "VALID"
        assert "timestamp" in logged_data


class TestHandler:
    """Test the main handler function"""

    @patch('backend.src.auth.verify_auth_challenge.verify_passcode')
    @patch('backend.src.auth.verify_auth_challenge.record_security_event')
    @patch('boto3.resource')
    def test_successful_verification(self, mock_boto_resource, mock_record, mock_verify):
        """Test successful passcode verification"""
        mock_verify.return_value = (True, "VALID")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "123456",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        assert result["response"]["answerCorrect"] is True
        
        # Verify security event was recorded
        mock_record.assert_called_once_with(
            email="user@example.com",
            event_type="EMAIL_PASSCODE",
            success=True,
            reason="VALID"
        )

    @patch('backend.src.auth.verify_auth_challenge.verify_passcode')
    @patch('backend.src.auth.verify_auth_challenge.record_security_event')
    @patch('boto3.resource')
    def test_failed_verification(self, mock_boto_resource, mock_record, mock_verify):
        """Test failed passcode verification"""
        mock_verify.return_value = (False, "INVALID_PASSCODE")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "999999",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        assert result["response"]["answerCorrect"] is False
        
        # Verify security event was recorded
        mock_record.assert_called_once_with(
            email="user@example.com",
            event_type="EMAIL_PASSCODE",
            success=False,
            reason="INVALID_PASSCODE"
        )

    def test_skips_non_custom_challenges(self):
        """Test that non-custom challenges are skipped"""
        event = {
            "request": {
                "challengeName": "SRP_AUTH",
                "challengeAnswer": "some_answer",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        result = handler(event, None)

        # Response should be unchanged
        assert result["response"] == {}

    @patch('backend.src.auth.verify_auth_challenge.record_security_event')
    @patch('boto3.resource')
    def test_handles_exceptions_gracefully(self, mock_boto_resource, mock_record):
        """Test graceful handling of exceptions"""
        mock_boto_resource.side_effect = Exception("DynamoDB error")

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "123456",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        result = handler(event, None)

        assert result["response"]["answerCorrect"] is False
        
        # Should still record security event
        mock_record.assert_called_once_with(
            email="user@example.com",
            event_type="EMAIL_PASSCODE",
            success=False,
            reason="VERIFICATION_ERROR"
        )

    def test_handles_missing_email(self):
        """Test handling of missing email attribute"""
        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "123456",
                "userAttributes": {}
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        assert result["response"]["answerCorrect"] is False

    def test_handles_empty_challenge_answer(self):
        """Test handling of empty challenge answer"""
        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        assert result["response"]["answerCorrect"] is False

    @patch('logging.Logger.warning')
    @patch('backend.src.auth.verify_auth_challenge.verify_passcode')
    @patch('boto3.resource')
    def test_logs_failed_verifications(self, mock_boto_resource, mock_verify, mock_logger):
        """Test that failed verifications are logged"""
        mock_verify.return_value = (False, "EXPIRED")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "123456",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            handler(event, None)

        mock_logger.assert_called_once()
        log_message = mock_logger.call_args[0][0]
        assert "Failed passcode verification" in log_message
        assert "user@example.com" in log_message
        assert "EXPIRED" in log_message

    @patch('logging.Logger.info')
    @patch('backend.src.auth.verify_auth_challenge.verify_passcode')
    @patch('boto3.resource')
    def test_logs_successful_verifications(self, mock_boto_resource, mock_verify, mock_logger):
        """Test that successful verifications are logged"""
        mock_verify.return_value = (True, "VALID")
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "challengeAnswer": "123456",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            handler(event, None)

        # Should have multiple log calls
        assert mock_logger.call_count >= 2
        
        # Check for success log
        success_logged = any(
            "Successful passcode verification" in str(call)
            for call in mock_logger.call_args_list
        )
        assert success_logged