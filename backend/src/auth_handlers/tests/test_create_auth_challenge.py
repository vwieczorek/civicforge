"""
Tests for Create Auth Challenge Lambda Trigger
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import ClientError
from ..create_auth_challenge import (
    handler, generate_passcode, store_passcode, 
    send_passcode_email, PASSCODE_LENGTH, PASSCODE_EXPIRY_MINUTES
)


class TestGeneratePasscode:
    """Test passcode generation"""

    def test_generates_correct_length(self):
        """Test that passcode has correct length"""
        passcode = generate_passcode()
        assert len(passcode) == PASSCODE_LENGTH

    def test_generates_only_digits(self):
        """Test that passcode contains only digits"""
        passcode = generate_passcode()
        assert passcode.isdigit()

    def test_generates_different_codes(self):
        """Test that consecutive calls generate different codes"""
        codes = [generate_passcode() for _ in range(10)]
        # Should have at least 9 unique codes out of 10
        assert len(set(codes)) >= 9


class TestStorePasscode:
    """Test passcode storage in DynamoDB"""

    @patch('boto3.resource')
    def test_stores_passcode_with_ttl(self, mock_boto_resource):
        """Test that passcode is stored with correct TTL"""
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        email = "test@example.com"
        passcode = "123456"
        
        store_passcode(email, passcode, mock_table)

        # Verify put_item was called
        mock_table.put_item.assert_called_once()
        
        # Check the stored item
        stored_item = mock_table.put_item.call_args[1]["Item"]
        assert stored_item["email"] == email
        assert stored_item["passcode"] == passcode
        assert stored_item["attempts"] == 0
        assert "created_at" in stored_item
        assert "expires_at" in stored_item
        assert "ttl" in stored_item
        
        # Verify TTL is approximately correct (within 1 minute)
        expected_ttl = int((datetime.utcnow() + timedelta(minutes=PASSCODE_EXPIRY_MINUTES)).timestamp())
        assert abs(stored_item["ttl"] - expected_ttl) < 60


class TestSendPasscodeEmail:
    """Test email sending functionality"""

    @patch('boto3.client')
    def test_sends_email_successfully(self, mock_boto_client):
        """Test successful email sending"""
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        email = "test@example.com"
        passcode = "123456"
        
        result = send_passcode_email(email, passcode)

        assert result is True
        
        # Verify SES was called correctly
        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args[1]
        
        assert call_args["Source"] == os.environ.get("FROM_EMAIL", "noreply@civicforge.org")
        assert call_args["Destination"]["ToAddresses"] == [email]
        assert passcode in call_args["Message"]["Body"]["Html"]["Data"]
        assert passcode in call_args["Message"]["Body"]["Text"]["Data"]

    @patch('boto3.client')
    def test_handles_ses_error(self, mock_boto_client):
        """Test handling of SES errors"""
        mock_ses = MagicMock()
        mock_ses.send_email.side_effect = ClientError(
            {"Error": {"Code": "MessageRejected"}}, 
            "SendEmail"
        )
        mock_boto_client.return_value = mock_ses

        result = send_passcode_email("test@example.com", "123456")

        assert result is False


class TestHandler:
    """Test the main handler function"""

    @patch('backend.src.auth.create_auth_challenge.send_passcode_email')
    @patch('backend.src.auth.create_auth_challenge.store_passcode')
    @patch('backend.src.auth.create_auth_challenge.generate_passcode')
    @patch('boto3.resource')
    def test_successful_challenge_creation(self, mock_boto_resource, mock_generate, 
                                         mock_store, mock_send):
        """Test successful passcode generation and sending"""
        mock_generate.return_value = "654321"
        mock_send.return_value = True
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        # Verify passcode was generated and stored
        mock_generate.assert_called_once()
        mock_store.assert_called_once_with("user@example.com", "654321", mock_table)
        mock_send.assert_called_once_with("user@example.com", "654321")

        # Check response
        assert result["response"]["publicChallengeParameters"]["email"] == "user@example.com"
        assert result["response"]["publicChallengeParameters"]["challengeType"] == "EMAIL_PASSCODE"
        assert result["response"]["privateChallengeParameters"]["passcode"] == "654321"
        assert result["response"]["challengeMetadata"] == "EMAIL_PASSCODE"

    def test_skips_non_custom_challenges(self):
        """Test that non-custom challenges are skipped"""
        event = {
            "request": {
                "challengeName": "SRP_AUTH",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        result = handler(event, None)

        # Response should be unchanged
        assert result["response"] == {}

    @patch('backend.src.auth.create_auth_challenge.send_passcode_email')
    @patch('backend.src.auth.create_auth_challenge.store_passcode')
    @patch('boto3.resource')
    def test_continues_on_email_failure(self, mock_boto_resource, mock_store, mock_send):
        """Test that authentication continues even if email fails"""
        mock_send.return_value = False
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        # Should still return challenge parameters
        assert "publicChallengeParameters" in result["response"]
        assert "privateChallengeParameters" in result["response"]

    @patch('boto3.resource')
    def test_handles_exceptions_gracefully(self, mock_boto_resource):
        """Test graceful handling of exceptions"""
        mock_boto_resource.side_effect = Exception("DynamoDB error")

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        result = handler(event, None)

        # Should return error in public parameters
        assert result["response"]["publicChallengeParameters"]["error"] == "CHALLENGE_CREATION_FAILED"
        assert "privateChallengeParameters" not in result["response"]

    def test_handles_missing_email(self):
        """Test handling of missing email attribute"""
        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "userAttributes": {}
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            result = handler(event, None)

        # Should handle gracefully
        assert "publicChallengeParameters" in result["response"]

    @patch('logging.Logger.info')
    @patch('backend.src.auth.create_auth_challenge.send_passcode_email')
    @patch('backend.src.auth.create_auth_challenge.store_passcode')
    @patch('boto3.resource')
    def test_logging(self, mock_boto_resource, mock_store, mock_send, mock_logger):
        """Test that appropriate logging occurs"""
        mock_send.return_value = True
        mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = mock_table

        event = {
            "request": {
                "challengeName": "CUSTOM_CHALLENGE",
                "userAttributes": {
                    "email": "user@example.com"
                }
            },
            "response": {}
        }

        with patch.dict(os.environ, {"PASSCODES_TABLE": "test-table"}):
            handler(event, None)

        # Should log request and response
        assert mock_logger.call_count >= 2
        
        # Check that sensitive data is not logged
        for call in mock_logger.call_args_list:
            log_message = str(call)
            assert "privateChallengeParameters" not in log_message

    def test_email_template_content(self):
        """Test that email template contains required elements"""
        from ..create_auth_challenge import send_passcode_email
        
        # Mock SES to capture the email content
        with patch('boto3.client') as mock_boto_client:
            mock_ses = MagicMock()
            mock_ses.send_email.return_value = {"MessageId": "test-id"}
            mock_boto_client.return_value = mock_ses
            
            send_passcode_email("test@example.com", "123456")
            
            call_args = mock_ses.send_email.call_args[1]
            html_body = call_args["Message"]["Body"]["Html"]["Data"]
            text_body = call_args["Message"]["Body"]["Text"]["Data"]
            
            # Check HTML version
            assert "123456" in html_body
            assert "CivicForge" in html_body
            assert f"{PASSCODE_EXPIRY_MINUTES} minutes" in html_body
            assert "didn't request this code" in html_body
            
            # Check text version
            assert "123456" in text_body
            assert "CivicForge" in text_body
            assert f"{PASSCODE_EXPIRY_MINUTES} minutes" in text_body