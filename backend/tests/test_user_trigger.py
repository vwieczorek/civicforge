"""
Tests for the Cognito PostConfirmation user creation trigger.
"""

import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError


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


def test_create_user_success(sample_cognito_event):
    """Test successful user creation"""
    with patch.dict('os.environ', {'USERS_TABLE_NAME': 'test-users'}):
        # FIX: Patch the 'table' object directly where it is used by the handler
        with patch('src.triggers.create_user.table') as mock_table:
            # Import after patching
            from src.triggers.create_user import handler
            
            # Execute the handler
            result = handler(sample_cognito_event, {})
            
            # Verify the result
            assert result == sample_cognito_event
            
            # Verify put_item was called
            mock_table.put_item.assert_called_once()
            call_args = mock_table.put_item.call_args[1]
            
            assert 'Item' in call_args
            item = call_args['Item']
            assert item['userId'] == '12345678-1234-1234-1234-123456789012'
            assert item['username'] == 'testuser123'
            assert item['email'] == 'test@example.com'
            assert item['reputation'] == 0
            assert item['experience'] == 0
            assert item['questCreationPoints'] == 10


def test_create_user_already_exists(sample_cognito_event):
    """Test idempotency - user already exists"""
    with patch.dict('os.environ', {'USERS_TABLE_NAME': 'test-users'}):
        # FIX: Patch the 'table' object directly
        with patch('src.triggers.create_user.table') as mock_table:
            # Mock that put_item fails with ConditionalCheckFailedException
            error_response = {'Error': {'Code': 'ConditionalCheckFailedException'}}
            mock_table.put_item.side_effect = ClientError(error_response, 'PutItem')
            
            # Import after patching
            from src.triggers.create_user import handler
            
            # Execute the handler - should handle the error gracefully
            result = handler(sample_cognito_event, {})
            
            # Verify the result
            assert result == sample_cognito_event
            
            # Verify put_item was attempted
            mock_table.put_item.assert_called_once()


def test_create_user_graceful_failure(sample_cognito_event):
    """Test graceful failure handling"""
    with patch.dict('os.environ', {'USERS_TABLE_NAME': 'test-users'}):
        # FIX: Patch the 'table' object directly
        with patch('src.triggers.create_user.table') as mock_table:
            # Mock DynamoDB put_item failure
            mock_table.put_item.side_effect = Exception("DynamoDB error")
            
            # Import after patching
            from src.triggers.create_user import handler
            
            # Execute the handler - should not raise exception
            result = handler(sample_cognito_event, {})
            
            # Verify the result is still returned (graceful failure)
            assert result == sample_cognito_event
            
            # Verify put_item was attempted
            mock_table.put_item.assert_called_once()


def test_create_user_missing_email(sample_cognito_event):
    """Test user creation without email"""
    # Remove email from event
    del sample_cognito_event['request']['userAttributes']['email']
    
    with patch.dict('os.environ', {'USERS_TABLE_NAME': 'test-users'}):
        # FIX: Patch the 'table' object directly
        with patch('src.triggers.create_user.table') as mock_table:
            # Import after patching
            from src.triggers.create_user import handler
            
            # Execute the handler
            result = handler(sample_cognito_event, {})
            
            # Verify the result
            assert result == sample_cognito_event
            
            # Verify put_item was called
            mock_table.put_item.assert_called_once()
            call_args = mock_table.put_item.call_args[1]
            
            assert 'Item' in call_args
            item = call_args['Item']
            # Email should not be in the item or should be None
            assert 'email' not in item or item['email'] is None


@pytest.mark.parametrize("missing_env", ["USERS_TABLE_NAME"])
def test_missing_environment_variables(missing_env):
    """Test that missing environment variables raise errors on import"""
    import sys
    
    # Remove the module from cache first
    if 'src.triggers.create_user' in sys.modules:
        del sys.modules['src.triggers.create_user']
    
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="Missing required environment variable"):
            import src.triggers.create_user
