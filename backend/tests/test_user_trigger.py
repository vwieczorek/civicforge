"""
Tests for the Cognito PostConfirmation user creation trigger.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime


@pytest.fixture
def sample_cognito_event():
    """Sample Cognito PostConfirmation event"""
    return {
        "version": "1",
        "region": "us-east-1",
        "userPoolId": "us-east-1_example",
        "userName": "testuser123",
        "callerContext": {
            "awsRequestId": "example-request-id"
        },
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "request": {
            "userAttributes": {
                "sub": "12345678-1234-1234-1234-123456789012",
                "email_verified": "true",
                "email": "test@example.com"
            }
        },
        "response": {}
    }


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    with patch.dict('os.environ', {'USERS_TABLE_NAME': 'test-users-table'}):
        yield


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB table"""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table


def test_create_user_success(sample_cognito_event, mock_env, mock_dynamodb):
    """Test successful user creation"""
    from src.triggers.create_user import handler
    
    # Mock that user doesn't exist yet
    mock_dynamodb.get_item.return_value = {}
    
    # Execute the handler
    result = handler(sample_cognito_event, {})
    
    # Verify the result
    assert result == sample_cognito_event
    
    # Verify DynamoDB calls
    mock_dynamodb.get_item.assert_called_once_with(
        Key={'userId': '12345678-1234-1234-1234-123456789012'}
    )
    
    # Verify put_item was called with correct structure
    mock_dynamodb.put_item.assert_called_once()
    put_call_args = mock_dynamodb.put_item.call_args[1]['Item']
    
    assert put_call_args['userId'] == '12345678-1234-1234-1234-123456789012'
    assert put_call_args['username'] == 'testuser123'
    assert put_call_args['email'] == 'test@example.com'
    assert put_call_args['reputation'] == 0
    assert put_call_args['experience'] == 0
    assert put_call_args['questCreationPoints'] == 10
    assert 'createdAt' in put_call_args
    assert 'updatedAt' in put_call_args


def test_create_user_already_exists(sample_cognito_event, mock_env, mock_dynamodb):
    """Test idempotency - user already exists"""
    from src.triggers.create_user import handler
    
    # Mock that user already exists
    mock_dynamodb.get_item.return_value = {
        'Item': {'userId': '12345678-1234-1234-1234-123456789012'}
    }
    
    # Execute the handler
    result = handler(sample_cognito_event, {})
    
    # Verify the result
    assert result == sample_cognito_event
    
    # Verify get_item was called but put_item was not
    mock_dynamodb.get_item.assert_called_once()
    mock_dynamodb.put_item.assert_not_called()


def test_create_user_graceful_failure(sample_cognito_event, mock_env, mock_dynamodb):
    """Test graceful failure handling"""
    from src.triggers.create_user import handler
    
    # Mock that user doesn't exist
    mock_dynamodb.get_item.return_value = {}
    
    # Mock DynamoDB put_item failure
    mock_dynamodb.put_item.side_effect = Exception("DynamoDB error")
    
    # Execute the handler - should not raise exception
    result = handler(sample_cognito_event, {})
    
    # Verify the result is still returned (graceful failure)
    assert result == sample_cognito_event
    
    # Verify put_item was attempted
    mock_dynamodb.put_item.assert_called_once()


def test_create_user_missing_email(sample_cognito_event, mock_env, mock_dynamodb):
    """Test user creation without email"""
    from src.triggers.create_user import handler
    
    # Remove email from event
    del sample_cognito_event['request']['userAttributes']['email']
    
    # Mock that user doesn't exist
    mock_dynamodb.get_item.return_value = {}
    
    # Execute the handler
    result = handler(sample_cognito_event, {})
    
    # Verify the result
    assert result == sample_cognito_event
    
    # Verify put_item was called without email
    mock_dynamodb.put_item.assert_called_once()
    put_call_args = mock_dynamodb.put_item.call_args[1]['Item']
    
    assert 'email' not in put_call_args
    assert put_call_args['userId'] == '12345678-1234-1234-1234-123456789012'


@pytest.mark.parametrize("missing_env", ["USERS_TABLE_NAME"])
def test_missing_environment_variables(missing_env):
    """Test that missing environment variables raise errors on import"""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="Missing required environment variable"):
            # This should fail on module import
            import importlib
            import sys
            if 'src.triggers.create_user' in sys.modules:
                importlib.reload(sys.modules['src.triggers.create_user'])
            else:
                import src.triggers.create_user