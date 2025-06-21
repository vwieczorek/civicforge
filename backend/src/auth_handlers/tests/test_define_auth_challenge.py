"""
Tests for Define Auth Challenge Lambda Trigger
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from ..define_auth_challenge import handler


class TestDefineAuthChallenge:
    """Test cases for define auth challenge Lambda"""

    def test_new_auth_attempt_starts_custom_challenge(self):
        """Test that new authentication attempts start with custom challenge"""
        event = {
            "request": {
                "session": []
            },
            "response": {}
        }

        result = handler(event, None)

        assert result["response"]["challengeName"] == "CUSTOM_CHALLENGE"
        assert result["response"]["issueTokens"] is False
        assert result["response"]["failAuthentication"] is False

    def test_successful_custom_challenge_issues_tokens(self):
        """Test that correct challenge response issues tokens"""
        event = {
            "request": {
                "session": [
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": True
                    }
                ]
            },
            "response": {}
        }

        result = handler(event, None)

        assert result["response"]["issueTokens"] is True
        assert result["response"]["failAuthentication"] is False

    def test_failed_challenge_allows_retry(self):
        """Test that failed challenge allows retry up to 3 times"""
        event = {
            "request": {
                "session": [
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": False
                    }
                ]
            },
            "response": {}
        }

        result = handler(event, None)

        assert result["response"]["challengeName"] == "CUSTOM_CHALLENGE"
        assert result["response"]["issueTokens"] is False
        assert result["response"]["failAuthentication"] is False

    def test_max_attempts_fails_authentication(self):
        """Test that 3 failed attempts fail authentication"""
        event = {
            "request": {
                "session": [
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": False
                    },
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": False
                    },
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": False
                    }
                ]
            },
            "response": {}
        }

        result = handler(event, None)

        assert result["response"]["failAuthentication"] is True
        assert result["response"]["issueTokens"] is False

    def test_mixed_session_history(self):
        """Test handling of mixed success/failure in session"""
        event = {
            "request": {
                "session": [
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": False
                    },
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": True
                    }
                ]
            },
            "response": {}
        }

        result = handler(event, None)

        # Should issue tokens since last challenge was successful
        assert result["response"]["issueTokens"] is True
        assert result["response"]["failAuthentication"] is False

    def test_empty_session_object(self):
        """Test handling of empty session object"""
        event = {
            "request": {},
            "response": {}
        }

        result = handler(event, None)

        # Should start with custom challenge
        assert result["response"]["challengeName"] == "CUSTOM_CHALLENGE"
        assert result["response"]["issueTokens"] is False
        assert result["response"]["failAuthentication"] is False

    @patch('logging.Logger.info')
    def test_logging(self, mock_logger):
        """Test that appropriate logging occurs"""
        event = {
            "request": {
                "session": []
            },
            "response": {}
        }

        handler(event, None)

        # Should log both request and response
        assert mock_logger.call_count == 2
        
        # Check that event is logged
        first_call = mock_logger.call_args_list[0][0][0]
        assert "Define auth challenge event:" in first_call
        
        # Check that response is logged
        second_call = mock_logger.call_args_list[1][0][0]
        assert "Define auth challenge response:" in second_call

    def test_preserves_existing_response_fields(self):
        """Test that existing response fields are preserved"""
        event = {
            "request": {
                "session": []
            },
            "response": {
                "someOtherField": "value"
            }
        }

        result = handler(event, None)

        assert result["response"]["someOtherField"] == "value"
        assert result["response"]["challengeName"] == "CUSTOM_CHALLENGE"

    def test_handles_malformed_session_entries(self):
        """Test graceful handling of malformed session entries"""
        event = {
            "request": {
                "session": [
                    None,
                    {},
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        # Missing challengeResult
                    },
                    {
                        "challengeName": "CUSTOM_CHALLENGE",
                        "challengeResult": True
                    }
                ]
            },
            "response": {}
        }

        result = handler(event, None)

        # Should still process successfully
        assert result["response"]["issueTokens"] is True
        assert result["response"]["failAuthentication"] is False