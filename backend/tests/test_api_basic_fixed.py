"""
Fixed basic API tests that work with the refactored handler structure
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.models import Quest, User, QuestStatus
from datetime import datetime


class MockDBClient:
    """A mock db_client that can be shared across all router imports"""
    def __init__(self):
        # Default mock methods - tests can override these
        self.get_user = AsyncMock()
        self.deduct_quest_creation_points = AsyncMock()
        self.create_quest = AsyncMock()
        self.list_quests = AsyncMock()
        self.get_quest = AsyncMock()
        self.update_user_wallet = AsyncMock()
        self.claim_quest_atomic = AsyncMock()
        self.submit_quest_atomic = AsyncMock()
        self.add_attestation_atomic = AsyncMock()
        self.complete_quest_atomic = AsyncMock()
        self.award_rewards = AsyncMock()
        self.award_quest_points = AsyncMock()
        self.delete_quest_atomic = AsyncMock()
        self.dispute_quest_atomic = AsyncMock()
        self.get_user_created_quests = AsyncMock()
        self.get_user_performed_quests = AsyncMock()


@pytest.fixture
def mock_db_client():
    """Mock the db_client to avoid AWS calls"""
    mock_client = MockDBClient()
    
    # Patch all locations where db_client is imported
    with patch('src.routers.quests_create.db_client', mock_client), \
         patch('src.routers.quests_read.db_client', mock_client), \
         patch('src.routers.quests_actions.db_client', mock_client), \
         patch('src.routers.quests_attest.db_client', mock_client), \
         patch('src.routers.quests_delete.db_client', mock_client), \
         patch('src.routers.users.db_client', mock_client):
        yield mock_client


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return User(
        userId="test-user-123",
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
        createdAt=datetime.utcnow(),
        attestations=[]
    )


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_feature_flags_endpoint(authenticated_client):
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
    # Set up mocks
    mock_db_client.get_user.return_value = sample_user
    mock_db_client.deduct_quest_creation_points.return_value = True
    mock_db_client.create_quest.return_value = sample_quest
    
    quest_data = {
        "title": "Test Quest",
        "description": "A test quest to verify API functionality",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Quest"
    assert data["status"] == "OPEN"


def test_create_quest_insufficient_points(authenticated_client, mock_db_client):
    """Test quest creation with insufficient points"""
    client = authenticated_client()
    # Mock user with no points
    user_no_points = User(
        userId="test-user-123",
        username="testuser",
        experience=100,
        reputation=50,
        questCreationPoints=0,  # No points
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    mock_db_client.get_user.return_value = user_no_points
    
    quest_data = {
        "title": "Test Quest",
        "description": "A test quest to verify API functionality",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 429
    assert "Insufficient quest creation points" in response.json()["detail"]


def test_get_quest_success(authenticated_client, mock_db_client, sample_quest):
    """Test getting a quest by ID"""
    client = authenticated_client()
    mock_db_client.get_quest.return_value = sample_quest
    
    response = client.get("/api/v1/quests/quest-123")
    assert response.status_code == 200
    data = response.json()
    assert data["questId"] == "quest-123"
    assert data["title"] == "Test Quest"


def test_get_quest_not_found(authenticated_client, mock_db_client):
    """Test getting a non-existent quest"""
    client = authenticated_client()
    mock_db_client.get_quest.return_value = None
    
    response = client.get("/api/v1/quests/nonexistent")
    assert response.status_code == 404
    assert "Quest not found" in response.json()["detail"]


def test_list_quests_success(authenticated_client, mock_db_client, sample_quest):
    """Test listing quests"""
    client = authenticated_client()
    mock_db_client.list_quests.return_value = [sample_quest]
    
    response = client.get("/api/v1/quests")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["questId"] == "quest-123"


def test_update_wallet_address_success(authenticated_client, mock_db_client):
    """Test updating user wallet address"""
    client = authenticated_client()
    mock_db_client.update_user_wallet.return_value = None
    
    # Valid checksum address
    wallet_data = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
    
    response = client.put("/api/v1/users/wallet", json=wallet_data)
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]


def test_update_wallet_address_invalid_format(authenticated_client):
    """Test updating wallet with invalid format"""
    client = authenticated_client()
    
    # Invalid address format
    wallet_data = "invalid-address"
    
    response = client.put("/api/v1/users/wallet", json=wallet_data)
    assert response.status_code == 400
    assert "Invalid Ethereum wallet address format" in response.json()["detail"]


def test_update_wallet_address_invalid_checksum(authenticated_client):
    """Test updating wallet with invalid checksum"""
    client = authenticated_client()
    
    # Valid format but invalid checksum
    wallet_data = "0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"
    
    response = client.put("/api/v1/users/wallet", json=wallet_data)
    assert response.status_code == 400
    assert "Invalid Ethereum wallet address checksum" in response.json()["detail"]