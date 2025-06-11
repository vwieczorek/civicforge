"""
Basic API tests to verify the endpoints work without complex DynamoDB integration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from handler import app
from src.models import Quest, User, QuestStatus
from datetime import datetime


@pytest.fixture
def mock_db_client():
    """Mock the db_client to avoid AWS calls"""
    with patch('src.routes.db_client') as mock:
        yield mock


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return User(
        userId="test-user-123",
        email="test@example.com",
        username="testuser",
        experience=100,
        reputation=50,
        questCreationPoints=10,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )


@pytest.fixture
def sample_quest():
    """Sample quest for testing"""
    return Quest(
        questId="quest-123",
        creatorId="test-user-123",
        title="Test Quest",
        description="A test quest for API testing",
        status=QuestStatus.OPEN,
        rewardXp=100,
        rewardReputation=10,
        createdAt=datetime.utcnow()
    )


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_feature_flags_endpoint(authenticated_client, mock_dynamodb_tables):
    """Test feature flags endpoint"""
    client = authenticated_client()
    response = client.get("/api/v1/feature-flags")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "reward_distribution" in data
    assert "signature_attestation" in data
    assert "dispute_resolution" in data


def test_create_quest_success(authenticated_client, mock_db_client, sample_user, sample_quest):
    """Test successful quest creation"""
    client = authenticated_client()
    # Mock the database calls
    mock_db_client.get_user = AsyncMock(return_value=sample_user)
    mock_db_client.deduct_quest_creation_points = AsyncMock(return_value=True)
    mock_db_client.create_quest = AsyncMock(return_value=sample_quest)
    
    quest_data = {
        "title": "New Test Quest",
        "description": "A test quest to verify API functionality",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Quest"  # From sample_quest
    assert data["status"] == "OPEN"


def test_create_quest_insufficient_points(authenticated_client, mock_db_client):
    """Test quest creation with insufficient points"""
    client = authenticated_client()
    # Mock user with no points
    user_no_points = User(
        userId="test-user-123",
        email="test@example.com", 
        username="testuser",
        experience=100,
        reputation=50,
        questCreationPoints=0,  # No points
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    mock_db_client.get_user = AsyncMock(return_value=user_no_points)
    
    quest_data = {
        "title": "New Test Quest",
        "description": "A test quest that should fail",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 429
    data = response.json()
    assert "Insufficient quest creation points" in data["error"]


def test_create_quest_user_not_found(authenticated_client, mock_db_client):
    """Test quest creation when user doesn't exist"""
    mock_db_client.get_user = AsyncMock(return_value=None)
    
    quest_data = {
        "title": "New Test Quest",
        "description": "A test quest that should fail",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    client = authenticated_client()
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["error"]


def test_get_quest_success(authenticated_client, mock_db_client, sample_quest):
    """Test successful quest retrieval"""
    mock_db_client.get_quest = AsyncMock(return_value=sample_quest)
    
    client = authenticated_client()
    response = client.get("/api/v1/quests/quest-123")
    assert response.status_code == 200
    data = response.json()
    assert data["questId"] == "quest-123"
    assert data["title"] == "Test Quest"


def test_get_quest_not_found(authenticated_client, mock_db_client):
    """Test quest retrieval when quest doesn't exist"""
    mock_db_client.get_quest = AsyncMock(return_value=None)
    
    client = authenticated_client()
    response = client.get("/api/v1/quests/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "Quest not found" in data["error"]


def test_list_quests_success(authenticated_client, mock_db_client, sample_quest):
    """Test successful quest listing"""
    mock_db_client.list_quests = AsyncMock(return_value=[sample_quest])
    
    client = authenticated_client()
    response = client.get("/api/v1/quests")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["questId"] == "quest-123"


def test_update_wallet_address_success(authenticated_client, mock_db_client):
    """Test successful wallet address update"""
    mock_db_client.update_user_wallet = AsyncMock(return_value=None)
    
    # Valid Ethereum address with proper checksum
    valid_address = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
    
    client = authenticated_client()
    response = client.put("/api/v1/users/wallet", json=valid_address)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Wallet address updated successfully"
    assert data["address"] == valid_address


def test_update_wallet_address_invalid_format(authenticated_client, mock_db_client):
    """Test wallet address update with invalid format"""
    invalid_address = "not-an-ethereum-address"
    
    client = authenticated_client()
    response = client.put("/api/v1/users/wallet", json=invalid_address)
    assert response.status_code == 400
    data = response.json()
    assert "Invalid Ethereum wallet address format" in data["error"]


def test_update_wallet_address_invalid_checksum(authenticated_client, mock_db_client):
    """Test wallet address update with invalid checksum"""
    # Address with wrong checksum
    invalid_checksum = "0x5aAeb6053f3e94c9b9a09f33669435e7ef1beaed"
    
    client = authenticated_client()
    response = client.put("/api/v1/users/wallet", json=invalid_checksum)
    assert response.status_code == 400
    data = response.json()
    assert "Invalid Ethereum wallet address checksum" in data["error"]