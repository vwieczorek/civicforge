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
from typing import Generator, Optional
import aiobotocore.session
import socket
from contextlib import closing

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
        except:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(f"Moto server failed to start on port {port}")
    
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
    except:
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
    except:
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
    except:
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
        'email': 'creator@example.com',
        'username': 'creator',
        'experience': 1000,
        'reputation': 100,
        'questCreationPoints': 10,
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    })
    
    users_table.put_item(Item={
        'userId': 'performer-456', 
        'email': 'performer@example.com',
        'username': 'performer',
        'experience': 500,
        'reputation': 50,
        'questCreationPoints': 5,
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    })
    
    yield moto_server


@pytest.fixture
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    from handler import app
    from src.db import db_client
    
    yield TestClient(app)
    
    # Cleanup
    app.dependency_overrides.clear()
    # Reset db_client between tests
    if hasattr(db_client, '_client') and db_client._client:
        # Can't await in sync fixture, so just mark for reset
        db_client._client = None


@pytest.fixture
def authenticated_client(client):
    """
    Provides a client with dependency overrides for authentication.
    Supports both specific users and custom user IDs.
    """
    from handler import app
    from src.auth import get_current_user_id, require_auth
    
    # Store original overrides to restore them later
    original_overrides = app.dependency_overrides.copy()
    
    def _authenticated_client(user_id_key: str = None, custom_user_id: str = None):
        # Determine user ID
        if custom_user_id:
            user_id = custom_user_id
        elif user_id_key == 'creator_id':
            user_id = 'creator-123'
        elif user_id_key == 'performer_id':
            user_id = 'performer-456'
        else:
            user_id = "test-user-123"  # Default test user
        
        # Override both auth dependencies
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        app.dependency_overrides[require_auth] = lambda: user_id
        return client

    yield _authenticated_client

    # Teardown: Restore original overrides to prevent side-effects
    app.dependency_overrides = original_overrides