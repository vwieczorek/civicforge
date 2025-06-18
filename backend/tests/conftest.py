"""
Test configuration and fixtures
"""

import os
import pytest
from unittest.mock import patch
import asyncio
import subprocess
import time
import httpx
import socket
from contextlib import closing, contextmanager

# Set test environment variables before importing any modules
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

# Set test table names
os.environ["USERS_TABLE"] = "test-users"
os.environ["QUESTS_TABLE"] = "test-quests"
os.environ["FAILED_REWARDS_TABLE"] = "test-failed-rewards"
os.environ["COGNITO_USER_POOL_ID"] = "test-pool-id-123"
os.environ["COGNITO_APP_CLIENT_ID"] = "test-client-id-456"
os.environ["COGNITO_REGION"] = "us-east-1"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["FF_REWARD_DISTRIBUTION"] = "false"
os.environ["FF_SIGNATURE_ATTESTATION"] = "true" 
os.environ["FF_DISPUTE_RESOLUTION"] = "false"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_cognito_keys():
    """Mock the Cognito public keys endpoint for JWT verification"""
    mock_keys = {
        "keys": [
            {
                "alg": "RS256",
                "e": "AQAB",
                "kid": "test-key-id",
                "kty": "RSA",
                "n": "test-modulus",
                "use": "sig"
            }
        ]
    }
    
    with patch('httpx.get') as mock_get:
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_keys
        yield mock_keys

@pytest.fixture
def valid_jwt_token():
    """A mock valid JWT token for testing"""
    return "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3Qta2V5LWlkIn0.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZXhwIjo5OTk5OTk5OTk5LCJhdWQiOiJ0ZXN0LWNsaWVudC1pZC00NTYiLCJpc3MiOiJodHRwczovL2NvZ25pdG8taWRwLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3Rlc3QtcG9vbC1pZC0xMjMifQ.mock-signature"


def find_free_port():
    """Find a free port to run moto server on"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def moto_server():
    """Start moto server for the test session"""
    port = find_free_port()
    endpoint_url = f"http://127.0.0.1:{port}"
    
    # Start moto server
    proc = subprocess.Popen(
        f"moto_server -p {port}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = httpx.get(f"{endpoint_url}/")
            if response.status_code in [200, 404]:  # Moto might return either
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(f"Moto server failed to start on port {port}")
    
    # Set the endpoint URL for aiobotocore to use
    os.environ["DYNAMODB_ENDPOINT_URL"] = endpoint_url
    
    yield endpoint_url
    
    proc.terminate()
    proc.wait()


@pytest.fixture
async def dynamodb_tables(moto_server):
    """Create DynamoDB tables for testing using moto server"""
    import boto3
    from datetime import datetime
    
    # Create sync client to create tables
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=moto_server,
        region_name='us-east-1',
        aws_access_key_id='testing',
        aws_secret_access_key='testing'
    )
    
    # Create users table if it doesn't exist
    try:
        users_table = dynamodb.Table('test-users')
        users_table.load()
        # Table exists, clear it
        scan = users_table.scan()
        with users_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'userId': item['userId']})
    except Exception:
        # Table doesn't exist, create it
        users_table = dynamodb.create_table(
            TableName='test-users',
            KeySchema=[{'AttributeName': 'userId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'userId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        users_table.wait_until_exists()
    
    # Create quests table if it doesn't exist
    try:
        quests_table = dynamodb.Table('test-quests')
        quests_table.load()
        # Table exists, clear it
        scan = quests_table.scan()
        with quests_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'questId': item['questId']})
    except Exception:
        # Table doesn't exist, create it
        quests_table = dynamodb.create_table(
            TableName='test-quests',
            KeySchema=[{'AttributeName': 'questId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'questId', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'creatorId', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'StatusIndex',
                    'KeySchema': [{'AttributeName': 'status', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'CreatorIndex',
                    'KeySchema': [{'AttributeName': 'creatorId', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        quests_table.wait_until_exists()
    
    # Create failed rewards table if it doesn't exist
    try:
        failed_rewards_table = dynamodb.Table('test-failed-rewards')
        failed_rewards_table.load()
        # Table exists, clear it
        scan = failed_rewards_table.scan()
        with failed_rewards_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'recordId': item['recordId']})
    except Exception:
        # Table doesn't exist, create it
        failed_rewards_table = dynamodb.create_table(
            TableName='test-failed-rewards',
            KeySchema=[{'AttributeName': 'recordId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'recordId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        failed_rewards_table.wait_until_exists()
    
    # Seed test users
    users_table.put_item(Item={
        'userId': 'creator-123',
        'username': 'creator',
        'experience': 1000,
        'reputation': 100,
        'questCreationPoints': 10,
        'walletAddress': '0x1234567890123456789012345678901234567890',
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    })
    
    users_table.put_item(Item={
        'userId': 'performer-456', 
        'username': 'performer',
        'experience': 500,
        'reputation': 50,
        'questCreationPoints': 5,
        'walletAddress': '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    })
    
    yield moto_server


@pytest.fixture
async def client(dynamodb_tables):
    """Create test client with all routes included and mocked DB client."""
    from fastapi.testclient import TestClient
    from src.app_factory import create_app
    from src.db import get_db_client, DynamoDBClient
    
    # Create a test app with ALL routers to ensure complete test coverage
    from src.routers.quests_read import router as quests_read_router
    from src.routers.quests_create import router as quests_create_router
    from src.routers.quests_actions import router as quests_actions_router
    from src.routers.quests_attest import router as quests_attest_router
    from src.routers.quests_delete import router as quests_delete_router
    from src.routers.users import router as users_router
    from src.routers.system import router as system_router
    
    app = create_app(
        routers=[
            quests_read_router,
            quests_create_router,
            quests_actions_router,
            quests_attest_router,
            quests_delete_router,
            users_router,
            system_router
        ],
        title="CivicForge API - Test Suite",
        description="Complete test application with all routes"
    )
    
    # Create a test DynamoDBClient instance.
    # The moto_server fixture (via dynamodb_tables) sets DYNAMODB_ENDPOINT_URL,
    # so DynamoDBClient will automatically connect to the mock server.
    test_db_client_instance = DynamoDBClient()
    
    # Override the get_db_client dependency to use our test instance
    app.dependency_overrides[get_db_client] = lambda: test_db_client_instance
    
    yield TestClient(app)
    
    # Cleanup: clear dependency overrides
    app.dependency_overrides.clear()


# Note: authenticated_as is now created per-client in the authenticated_client fixture
# This ensures it uses the correct app instance for each test


@pytest.fixture
def authenticated_client(client):
    """
    Provides a client with an authentication helper.
    Use with authenticated_as context manager for proper isolation.
    """
    # Get the app from the test client
    app = client.app
    
    # Create a version of authenticated_as bound to this app
    @contextmanager
    def _authenticated_as(user_id: str):
        from src.auth import get_current_user_id, require_auth
        
        # Store original overrides
        original_overrides = app.dependency_overrides.copy()
        
        try:
            # Apply overrides
            app.dependency_overrides[get_current_user_id] = lambda: user_id
            app.dependency_overrides[require_auth] = lambda: user_id
            yield
        finally:
            # Restore original overrides
            app.dependency_overrides = original_overrides
    
    # Attach the context manager to the client for convenience
    client.authenticated_as = _authenticated_as
    
    # Also provide the old factory interface for easier migration
    def _authenticated_client(user_id_key: str = None, custom_user_id: str = None):
        # Determine user ID
        if custom_user_id:
            user_id = custom_user_id
        elif user_id_key == 'creator_id':
            user_id = 'creator-123'
        elif user_id_key == 'performer_id':
            user_id = 'performer-456'  
        elif user_id_key == 'performer1_id':
            user_id = 'performer1-789'
        elif user_id_key == 'performer2_id':
            user_id = 'performer2-999'
        elif user_id_key == 'unauthorized_id':
            user_id = 'unauthorized-789'
        else:
            user_id = "test-user-123"  # Default test user
        
        # Create a wrapper that applies auth on each request
        class AuthWrapper:
            def __init__(self, client, user_id):
                self.client = client
                self.user_id = user_id
                
            def __getattr__(self, name):
                # Pass through all attributes to the underlying client
                attr = getattr(self.client, name)
                if callable(attr) and name in ['get', 'post', 'put', 'delete', 'patch']:
                    # Wrap HTTP methods to apply auth
                    def wrapped(*args, **kwargs):
                        with _authenticated_as(self.user_id):
                            return attr(*args, **kwargs)
                    return wrapped
                return attr
        
        return AuthWrapper(client, user_id)

    yield _authenticated_client
    
    # Cleanup handled by authenticated_as context manager
    # No need for aggressive clear() here

@pytest.fixture
def mock_feature_flags():
    """Mock feature flags for tests"""
    with patch('src.feature_flags.is_enabled') as mock:
        # Enable all features by default in tests
        mock.return_value = True
        yield mock