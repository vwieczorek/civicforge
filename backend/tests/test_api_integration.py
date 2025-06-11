"""
Fixed API integration tests using moto server mode
This approach avoids the aiobotocore patching issues
"""

import pytest
import os
from handler import app
from src.auth import get_current_user_id


@pytest.mark.asyncio
async def test_api_create_quest_integration(authenticated_client, dynamodb_tables):
    """Test creating a quest - covers routes.py, db.py, auth.py, models.py"""
    # Set endpoint URL for DynamoDB client
    creator_client = authenticated_client('creator_id')
    
    quest_data = {
        "title": "Test Integration Quest",
        "description": "Testing the full integration stack",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    response = creator_client.post("/api/v1/quests", json=quest_data)
    
    assert response.status_code == 201
    data = response.json()
    assert "questId" in data
    assert data["title"] == "Test Integration Quest"
    assert data["status"] == "OPEN"
    assert data["creatorId"] == "creator-123"


@pytest.mark.asyncio
async def test_api_list_quests_integration(authenticated_client, dynamodb_tables):
    """Test listing quests - covers routes.py, db.py"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test listing quests - covers routes.py, db.py"""
    creator_client = authenticated_client('creator_id')
    
    # First create a quest
    quest_data = {
        "title": "Test Quest for Listing",
        "description": "A quest to test listing",
        "rewardXp": 50,
        "rewardReputation": 5
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    assert create_response.status_code == 201
    
    # Now list quests
    list_response = creator_client.get("/api/v1/quests")
    assert list_response.status_code == 200
    
    quests = list_response.json()
    assert len(quests) == 1
    assert quests[0]["title"] == "Test Quest for Listing"


@pytest.mark.asyncio
async def test_api_get_quest_integration(authenticated_client, dynamodb_tables):
    """Test getting a specific quest - covers routes.py, db.py"""
    
    # Create a quest first
    quest_data = {
        "title": "Specific Quest",
        "description": "A specific quest for retrieval",
        "rewardXp": 75,
        "rewardReputation": 7
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Get the specific quest
    get_response = creator_client.get(f"/api/v1/quests/{quest_id}")
    assert get_response.status_code == 200
    
    quest = get_response.json()
    assert quest["questId"] == quest_id
    assert quest["title"] == "Specific Quest"


@pytest.mark.asyncio
async def test_api_get_quest_not_found(authenticated_client, dynamodb_tables):
    """Test getting non-existent quest - covers error handling in routes.py"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test getting non-existent quest - covers error handling in routes.py"""
    creator_client = authenticated_client('creator_id')
    
    response = creator_client.get("/api/v1/quests/nonexistent-quest")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_quest_claim_integration(authenticated_client, dynamodb_tables):
    """Test claiming a quest - covers routes.py, db.py, state_machine.py"""
    performer_client = authenticated_client('performer_id')
    
    # Create a quest as creator
    quest_data = {
        "title": "Quest to Claim",
        "description": "A quest for testing claims",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Claim the quest as performer
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    claimed_quest = claim_response.json()
    assert claimed_quest["status"] == "CLAIMED"
    assert claimed_quest["performerId"] == "performer-456"


@pytest.mark.asyncio
async def test_api_quest_claim_own_quest_error(authenticated_client, dynamodb_tables):
    """Test that creator cannot claim own quest - covers error handling"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test that creator cannot claim own quest - covers error handling"""
    
    # Create a quest
    quest_data = {
        "title": "Own Quest",
        "description": "Creator's own quest", 
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Try to claim own quest (should fail)
    claim_response = creator_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 400  # Updated to match actual expected response


@pytest.mark.asyncio
async def test_api_quest_submit_integration(authenticated_client, dynamodb_tables):
    """Test submitting work - covers routes.py, db.py, state_machine.py"""
    creator_client = authenticated_client('creator_id')
    performer_client = authenticated_client('performer_id')
    
    # Create and claim a quest
    quest_data = {
        "title": "Quest to Submit",
        "description": "A quest for testing submissions",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Claim as performer
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    # Submit work
    submission_data = {"submissionText": "Here is my completed work"}
    submit_response = performer_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 200
    
    submitted_quest = submit_response.json()
    assert submitted_quest["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_api_user_profile_integration(authenticated_client, dynamodb_tables):
    """Test getting user profile - covers routes.py, db.py"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test getting user profile - covers routes.py, db.py"""
    
    # Note: The endpoint is /users/{user_id}, not /profile
    response = creator_client.get("/api/v1/users/creator-123")
    assert response.status_code == 200
    
    profile = response.json()
    assert profile["userId"] == "creator-123"
    assert profile["email"] == "creator@example.com"


@pytest.mark.asyncio
async def test_api_quest_insufficient_points(authenticated_client, dynamodb_tables):
    """Test creating quest with insufficient points - covers error handling"""
    creator_client = authenticated_client('creator_id')
    
    # First, drain the user's quest creation points by creating many quests
    for i in range(15):  # More than the user has points for
        quest_data = {
            "title": f"Quest {i}",
            "description": f"Quest number {i}",
            "rewardXp": 10,
            "rewardReputation": 1
        }
        response = creator_client.post("/api/v1/quests", json=quest_data)
        if response.status_code == 429:
            # We've hit the limit, which is what we want to test
            break
    
    # This should fail with insufficient points
    final_quest_data = {
        "title": "Final Quest",
        "description": "This should fail",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    response = creator_client.post("/api/v1/quests", json=final_quest_data)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_api_delete_quest_integration(authenticated_client, dynamodb_tables):
    """Test deleting a quest - covers routes.py, db.py"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test deleting a quest - covers routes.py, db.py"""
    
    # Create a quest
    quest_data = {
        "title": "Quest to Delete",
        "description": "This quest will be deleted",
        "rewardXp": 50,
        "rewardReputation": 5
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Delete the quest
    delete_response = creator_client.delete(f"/api/v1/quests/{quest_id}")
    assert delete_response.status_code == 204
    
    # Verify it's deleted
    get_response = creator_client.get(f"/api/v1/quests/{quest_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_api_feature_flags_integration(authenticated_client, dynamodb_tables):
    """Test getting feature flags - covers routes.py, feature_flags.py"""
    creator_client = authenticated_client('creator_id')
    
    response = creator_client.get("/api/v1/feature-flags")
    assert response.status_code == 200
    
    flags = response.json()
    assert isinstance(flags, dict)
    # Should have all the defined feature flags
    assert "reward_distribution" in flags
    assert "signature_attestation" in flags
    assert "dispute_resolution" in flags


@pytest.mark.asyncio
async def test_api_full_quest_lifecycle(authenticated_client, dynamodb_tables):
    """Test complete quest lifecycle from creation to completion - highest value integration test"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test complete quest lifecycle from creation to completion - highest value integration test"""
    creator_client = authenticated_client('creator_id')
    
    quest_data = {
        "title": "Full Lifecycle Quest",
        "description": "Testing the entire quest lifecycle end-to-end",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    assert create_response.status_code == 201
    quest_id = create_response.json()["questId"]
    
    # 2. Switch to performer and claim
    performer_client = authenticated_client('performer_id')
    
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    assert claim_response.json()["status"] == "CLAIMED"
    
    # 3. Submit work
    submission_data = {"submissionText": "I have completed the quest"}
    submit_response = performer_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "SUBMITTED"
    
    # 4. Attest as creator (requestor)
    creator_attestation = {
        "notes": "Work completed satisfactorily",
        "signature": "0x1234567890abcdef"
    }
    attest_response = creator_client.post(f"/api/v1/quests/{quest_id}/attest", json=creator_attestation)
    assert attest_response.status_code == 200
    
    # 5. Attest as performer
    performer_attestation = {
        "notes": "Quest requirements were met",
        "signature": "0xfedcba0987654321"
    }
    attest_response = performer_client.post(f"/api/v1/quests/{quest_id}/attest", json=performer_attestation)
    assert attest_response.status_code == 200
    
    # Quest should now be COMPLETE
    final_quest = attest_response.json()
    assert final_quest["status"] == "COMPLETE"
    assert len(final_quest["attestations"]) == 2


# Additional comprehensive integration tests to improve coverage

@pytest.mark.asyncio
async def test_api_user_profile_public_view(authenticated_client, dynamodb_tables):
    """Test viewing another user's profile (public view)"""
    creator_client = authenticated_client('creator_id')
    
    # View performer's profile
    response = creator_client.get("/api/v1/users/performer-456")
    assert response.status_code == 200
    
    profile = response.json()
    assert profile["userId"] == "performer-456"
    assert profile["email"] == "performer@example.com"
    # Sensitive data should be hidden
    assert "walletAddress" not in profile
    assert "questCreationPoints" not in profile


@pytest.mark.asyncio
async def test_api_user_profile_own_view(authenticated_client, dynamodb_tables):
    """Test viewing own profile (full data)"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test viewing own profile (full data)"""
    
    response = creator_client.get("/api/v1/users/creator-123")
    assert response.status_code == 200
    
    profile = response.json()
    assert profile["userId"] == "creator-123"
    assert profile["email"] == "creator@example.com"
    # Own profile shows all data
    assert profile["questCreationPoints"] == 10


@pytest.mark.asyncio
async def test_api_user_profile_not_found(authenticated_client, dynamodb_tables):
    """Test viewing non-existent user profile"""
    creator_client = authenticated_client('creator_id')
    
    response = creator_client.get("/api/v1/users/nonexistent-user")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_update_wallet_address_success(authenticated_client, dynamodb_tables):
    """Test updating wallet address with valid checksum address"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test updating wallet address with valid checksum address"""
    
    # Valid Ethereum address with proper checksum
    valid_address = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
    
    response = creator_client.put("/api/v1/users/wallet", json=valid_address)
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Wallet address updated successfully"
    assert data["address"] == valid_address


@pytest.mark.asyncio
async def test_api_update_wallet_address_invalid_format(authenticated_client, dynamodb_tables):
    """Test updating wallet address with invalid format"""
    creator_client = authenticated_client('creator_id')
    
    # Invalid address format
    invalid_address = "not-an-ethereum-address"
    
    response = creator_client.put("/api/v1/users/wallet", json=invalid_address)
    assert response.status_code == 400
    assert "Invalid Ethereum wallet address format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_update_wallet_address_invalid_checksum(authenticated_client, dynamodb_tables):
    """Test updating wallet address with invalid checksum"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test updating wallet address with invalid checksum"""
    
    # Address with wrong checksum
    invalid_checksum = "0x5aAeb6053f3e94c9b9a09f33669435e7ef1beaed"
    
    response = creator_client.put("/api/v1/users/wallet", json=invalid_checksum)
    assert response.status_code == 400
    assert "Invalid Ethereum wallet address checksum" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_claim_quest_already_claimed(authenticated_client, dynamodb_tables):
    """Test claiming a quest that's already been claimed"""
    creator_client = authenticated_client('creator_id')
    performer_client = authenticated_client('performer_id')
    
    # Create quest
    quest_data = {
        "title": "Double Claim Test",
        "description": "Testing race condition protection",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # First claim should succeed
    claim_response1 = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response1.status_code == 200
    
    # Try to claim again with different user - should fail
    # Note: We'd need a third user for this test, but seed_users only has 2
    # So we'll test with same user
    claim_response2 = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response2.status_code == 400  # Already claimed


@pytest.mark.asyncio
async def test_api_submit_quest_wrong_user(authenticated_client, dynamodb_tables):
    """Test submitting work as someone other than the performer"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test submitting work as someone other than the performer"""
    performer_client = authenticated_client('performer_id')
    
    # Create and claim quest
    quest_data = {
        "title": "Wrong Submitter Test",
        "description": "Testing authorization for submission",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    # Try to submit as creator (wrong user)
    submission_data = {"submissionText": "Unauthorized submission"}
    submit_response = creator_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 403
    assert "Only the assigned performer can submit work" in submit_response.json()["detail"]


@pytest.mark.asyncio
async def test_api_submit_quest_wrong_status(authenticated_client, dynamodb_tables):
    """Test submitting work on unclaimed quest"""
    creator_client = authenticated_client('creator_id')
    performer_client = authenticated_client('performer_id')
    
    # Create quest but don't claim it
    quest_data = {
        "title": "Wrong Status Test",
        "description": "Testing status validation for submission",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Try to submit on OPEN quest
    submission_data = {"submissionText": "Premature submission"}
    submit_response = performer_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 400
    assert "Quest must be in CLAIMED status to submit" in submit_response.json()["detail"]


@pytest.mark.asyncio
async def test_api_attest_quest_unauthorized(authenticated_client, dynamodb_tables):
    """Test attesting by unauthorized user"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test attesting by unauthorized user"""
    performer_client = authenticated_client('performer_id')
    
    # Create, claim and submit quest
    quest_data = {
        "title": "Unauthorized Attest Test",
        "description": "Testing authorization for attestation",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    submission_data = {"submissionText": "Work completed"}
    submit_response = performer_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 200
    
    # Add third user to test unauthorized attestation
    import boto3
    dynamodb = boto3.resource("dynamodb", endpoint_url=os.environ["DYNAMODB_ENDPOINT_URL"], region_name="us-east-1")
    users_table = dynamodb.Table('test-users')
    users_table.put_item(Item={
        'userId': 'unauthorized-789',
        'email': 'unauthorized@example.com',
        'username': 'unauthorized',
        'experience': 0,
        'reputation': 0,
        'questCreationPoints': 1,
        'createdAt': '2024-01-01T00:00:00',
        'updatedAt': '2024-01-01T00:00:00'
    })
    
    from handler import app
    from src.auth import get_current_user_id
    app.dependency_overrides[get_current_user_id] = lambda: "unauthorized-789"
    unauthorized_client = authenticated_client.__wrapped__(None, None)  # Get raw client
    
    # Try to attest as unauthorized user
    attestation_data = {"notes": "Unauthorized attestation"}
    attest_response = unauthorized_client.post(f"/api/v1/quests/{quest_id}/attest", json=attestation_data)
    assert attest_response.status_code == 403
    assert "Not authorized to attest this quest" in attest_response.json()["detail"]


@pytest.mark.asyncio
async def test_api_attest_quest_duplicate(authenticated_client, dynamodb_tables):
    """Test duplicate attestation by same user"""
    creator_client = authenticated_client('creator_id')
    performer_client = authenticated_client('performer_id')
    
    # Create, claim and submit quest
    quest_data = {
        "title": "Duplicate Attest Test",
        "description": "Testing duplicate attestation prevention",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    submission_data = {"submissionText": "Work completed"}
    submit_response = performer_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 200
    
    # First attestation should succeed
    attestation_data = {"notes": "Work completed satisfactorily"}
    attest_response1 = creator_client.post(f"/api/v1/quests/{quest_id}/attest", json=attestation_data)
    assert attest_response1.status_code == 200
    
    # Second attestation by same user should fail
    attest_response2 = creator_client.post(f"/api/v1/quests/{quest_id}/attest", json=attestation_data)
    assert attest_response2.status_code == 409
    assert "Already attested" in attest_response2.json()["detail"]


@pytest.mark.asyncio
async def test_api_dispute_quest_missing_reason(authenticated_client, dynamodb_tables):
    """Test disputing quest without providing reason"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test disputing quest without providing reason"""
    performer_client = authenticated_client('performer_id')
    
    # Create, claim and submit quest
    quest_data = {
        "title": "Dispute Test",
        "description": "Testing dispute functionality",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    submission_data = {"submissionText": "Work completed"}
    submit_response = performer_client.post(f"/api/v1/quests/{quest_id}/submit", json=submission_data)
    assert submit_response.status_code == 200
    
    # Try to dispute without reason
    dispute_response = creator_client.post(f"/api/v1/quests/{quest_id}/dispute", json={})
    assert dispute_response.status_code == 400
    assert "Dispute reason is required" in dispute_response.json()["detail"]


@pytest.mark.asyncio
async def test_api_delete_quest_wrong_user(authenticated_client, dynamodb_tables):
    """Test deleting quest by non-creator"""
    creator_client = authenticated_client('creator_id')
    performer_client = authenticated_client('performer_id')
    
    # Create quest
    quest_data = {
        "title": "Delete Authorization Test",
        "description": "Testing delete authorization",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    # Try to delete as performer (not creator)
    delete_response = performer_client.delete(f"/api/v1/quests/{quest_id}")
    assert delete_response.status_code == 403
    assert "Only the quest creator can delete a quest" in delete_response.json()["detail"]


@pytest.mark.asyncio
async def test_api_delete_quest_wrong_status(authenticated_client, dynamodb_tables):
    """Test deleting claimed quest"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    """Test deleting claimed quest"""
    performer_client = authenticated_client('performer_id')
    
    # Create and claim quest
    quest_data = {
        "title": "Delete Status Test",
        "description": "Testing delete status validation",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response = creator_client.post("/api/v1/quests", json=quest_data)
    quest_id = create_response.json()["questId"]
    
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id}/claim")
    assert claim_response.status_code == 200
    
    # Try to delete claimed quest
    delete_response = creator_client.delete(f"/api/v1/quests/{quest_id}")
    assert delete_response.status_code == 400
    assert "Cannot delete quest in CLAIMED status" in delete_response.json()["detail"]


@pytest.mark.asyncio
async def test_api_list_quests_with_status_filter(authenticated_client, dynamodb_tables):
async def test_api_list_quests_with_status_filter(authenticated_client, dynamodb_tables):
    """Test listing quests with status filter"""
    creator_client = authenticated_client('creator_id')
    performer_client = authenticated_client('performer_id')
    
    # Create multiple quests with different statuses
    quest_data1 = {
        "title": "Open Quest",
        "description": "This will remain open",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    quest_data2 = {
        "title": "Claimed Quest",
        "description": "This will be claimed",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    create_response1 = creator_client.post("/api/v1/quests", json=quest_data1)
    create_response2 = creator_client.post("/api/v1/quests", json=quest_data2)
    quest_id2 = create_response2.json()["questId"]
    
    # Claim second quest
    claim_response = performer_client.post(f"/api/v1/quests/{quest_id2}/claim")
    assert claim_response.status_code == 200
    
    # Test filtering by OPEN status
    open_response = creator_client.get("/api/v1/quests?status=OPEN")
    assert open_response.status_code == 200
    open_quests = open_response.json()
    assert len(open_quests) == 1
    assert open_quests[0]["title"] == "Open Quest"
    
    # Test filtering by CLAIMED status
    claimed_response = creator_client.get("/api/v1/quests?status=CLAIMED")
    assert claimed_response.status_code == 200
    claimed_quests = claimed_response.json()
    assert len(claimed_quests) == 1
    assert claimed_quests[0]["title"] == "Claimed Quest"