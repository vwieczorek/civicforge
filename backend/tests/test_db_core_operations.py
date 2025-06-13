"""
Test core database operations with comprehensive coverage
"""

import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
import uuid
from botocore.exceptions import ClientError

from src.db import DynamoDBClient
from src.models import Quest, QuestStatus, User, Attestation


@pytest.fixture
async def db_client(dynamodb_tables):
    """Create a DynamoDB client for testing"""
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    client = DynamoDBClient()
    return client


@pytest.fixture
async def test_user(db_client):
    """Create a test user"""
    user = User(
        userId="test-user-123",
        username="testuser",
        reputation=100,
        experience=0,
        questCreationPoints=1000,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )
    await db_client.create_user(user)
    return user


@pytest.fixture
async def test_quest(db_client, test_user):
    """Create a test quest"""
    quest = Quest(
        questId=str(uuid.uuid4()),
        creatorId=test_user.userId,
        title="Test Quest",
        description="This is a test quest for unit testing",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.OPEN,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        attestations=[]
    )
    await db_client.create_quest(quest)
    return quest


class TestCoreQuestLifecycle:
    """Test the core quest lifecycle operations"""
    
    @pytest.mark.asyncio
    async def test_create_and_get_quest(self, db_client, test_user):
        """Test creating a quest and retrieving it"""
        # Create quest
        quest = Quest(
            questId=str(uuid.uuid4()),
            creatorId=test_user.userId,
            title="Test Quest Creation",
            description="Testing quest creation and retrieval",
            rewardXp=50,
            rewardReputation=5,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        await db_client.create_quest(quest)
        
        # Get quest
        retrieved_quest = await db_client.get_quest(quest.questId)
        assert retrieved_quest is not None
        assert retrieved_quest.questId == quest.questId
        assert retrieved_quest.title == quest.title
        assert retrieved_quest.creatorId == quest.creatorId
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_quest(self, db_client):
        """Test getting a quest that doesn't exist"""
        result = await db_client.get_quest("nonexistent-quest-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_quest_handles_client_error(self, db_client):
        """Test that get_quest handles ClientError gracefully"""
        # Create a mock client that will be returned by the context manager
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.get_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError'}}, 
            'GetItem'
        )
        
        # Create a mock async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
    
        # Patch get_resource to return our mock context manager
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            result = await db_client.get_quest("some-quest-id")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_claim_quest_atomic_success(self, db_client, test_quest):
        """Test successfully claiming an open quest"""
        performer_id = "performer-456"
        
        # First verify the quest exists and is OPEN
        quest_before = await db_client.get_quest(test_quest.questId)
        assert quest_before is not None, "Quest not found"
        assert quest_before.status == QuestStatus.OPEN, f"Quest status is {quest_before.status}, not OPEN"
        
        success = await db_client.claim_quest_atomic(test_quest.questId, performer_id)
        assert success is True
        
        # Verify quest was claimed
        updated_quest = await db_client.get_quest(test_quest.questId)
        assert updated_quest.status == QuestStatus.CLAIMED
        assert updated_quest.performerId == performer_id
        assert updated_quest.claimedAt is not None
    
    @pytest.mark.asyncio
    async def test_claim_quest_atomic_already_claimed(self, db_client, test_quest):
        """Test claiming a quest that's already claimed"""
        performer1 = "performer-1"
        performer2 = "performer-2"
        
        # First claim should succeed
        success1 = await db_client.claim_quest_atomic(test_quest.questId, performer1)
        assert success1 is True
        
        # Second claim should fail (ConditionalCheckFailedException)
        success2 = await db_client.claim_quest_atomic(test_quest.questId, performer2)
        assert success2 is False
    
    @pytest.mark.asyncio
    async def test_claim_quest_atomic_handles_error(self, db_client, test_quest):
        """Test claim_quest_atomic handles non-conditional errors"""
        # Create a mock client
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError'}}, 
            'UpdateItem'
        )
        
        # Create a mock async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            with pytest.raises(ClientError):
                await db_client.claim_quest_atomic(test_quest.questId, "performer-id")
    
    @pytest.mark.asyncio
    async def test_submit_quest_atomic_success(self, db_client, test_quest):
        """Test successfully submitting a claimed quest"""
        performer_id = "performer-789"
        submission_text = "I completed the quest successfully!"
        
        # First claim the quest
        await db_client.claim_quest_atomic(test_quest.questId, performer_id)
        
        # Then submit it
        success = await db_client.submit_quest_atomic(
            test_quest.questId, 
            performer_id, 
            submission_text
        )
        assert success is True
        
        # Verify submission
        updated_quest = await db_client.get_quest(test_quest.questId)
        assert updated_quest.status == QuestStatus.SUBMITTED
        assert updated_quest.submissionText == submission_text
        assert updated_quest.submittedAt is not None
    
    @pytest.mark.asyncio
    async def test_submit_quest_atomic_wrong_performer(self, db_client, test_quest):
        """Test submitting a quest by wrong performer"""
        correct_performer = "performer-1"
        wrong_performer = "performer-2"
        
        # Claim with correct performer
        await db_client.claim_quest_atomic(test_quest.questId, correct_performer)
        
        # Try to submit with wrong performer
        success = await db_client.submit_quest_atomic(
            test_quest.questId,
            wrong_performer,
            "Trying to submit someone else's quest"
        )
        assert success is False
    
    @pytest.mark.asyncio
    async def test_submit_quest_atomic_wrong_status(self, db_client, test_quest):
        """Test submitting a quest that's not claimed"""
        # Try to submit an OPEN quest (not claimed)
        success = await db_client.submit_quest_atomic(
            test_quest.questId,
            "performer-id",
            "Trying to submit unclaimed quest"
        )
        assert success is False
    
    @pytest.mark.asyncio
    async def test_add_attestation_atomic_success(self, db_client, test_quest):
        """Test successfully adding an attestation"""
        performer_id = "performer-123"
        
        # Claim and submit the quest
        await db_client.claim_quest_atomic(test_quest.questId, performer_id)
        await db_client.submit_quest_atomic(
            test_quest.questId,
            performer_id,
            "Quest completed"
        )
        
        # Add requestor attestation
        attestation = Attestation(
            user_id=test_quest.creatorId,
            role="requestor",
            attested_at=datetime.now(timezone.utc),
            notes="Good work!"
        )
        
        success = await db_client.add_attestation_atomic(test_quest.questId, attestation.model_dump())
        assert success is True
        
        # Verify attestation was added
        updated_quest = await db_client.get_quest(test_quest.questId)
        assert len(updated_quest.attestations) == 1
        assert updated_quest.attestations[0].user_id == test_quest.creatorId
        assert updated_quest.hasRequestorAttestation is True
    
    @pytest.mark.asyncio
    async def test_add_attestation_atomic_duplicate(self, db_client, test_quest):
        """Test adding duplicate attestation fails"""
        performer_id = "performer-123"
        
        # Setup: claim and submit
        await db_client.claim_quest_atomic(test_quest.questId, performer_id)
        await db_client.submit_quest_atomic(test_quest.questId, performer_id, "Done")
        
        # Add first attestation
        attestation = Attestation(
            user_id=test_quest.creatorId,
            role="requestor",
            attested_at=datetime.now(timezone.utc)
        )
        await db_client.add_attestation_atomic(test_quest.questId, attestation.model_dump())
        
        # Try to add duplicate attestation
        success = await db_client.add_attestation_atomic(test_quest.questId, attestation.model_dump())
        assert success is False
    
    @pytest.mark.asyncio
    async def test_add_attestation_atomic_wrong_status(self, db_client, test_quest):
        """Test adding attestation to quest in wrong status"""
        # Try to add attestation to OPEN quest
        attestation = Attestation(
            user_id=test_quest.creatorId,
            role="requestor",
            attested_at=datetime.now(timezone.utc)
        )
        
        success = await db_client.add_attestation_atomic(test_quest.questId, attestation.model_dump())
        assert success is False
    
    @pytest.mark.asyncio
    async def test_complete_quest_atomic_success(self, db_client, test_quest):
        """Test successfully completing a quest"""
        performer_id = "performer-123"
        
        # Setup: claim, submit, and add both attestations
        await db_client.claim_quest_atomic(test_quest.questId, performer_id)
        await db_client.submit_quest_atomic(test_quest.questId, performer_id, "Done")
        
        # Add both attestations
        requestor_attestation = Attestation(
            user_id=test_quest.creatorId,
            role="requestor",
            attested_at=datetime.now(timezone.utc)
        )
        performer_attestation = Attestation(
            user_id=performer_id,
            role="performer",
            attested_at=datetime.now(timezone.utc)
        )
        
        await db_client.add_attestation_atomic(test_quest.questId, requestor_attestation.model_dump())
        await db_client.add_attestation_atomic(test_quest.questId, performer_attestation.model_dump())
        
        # Complete the quest
        success = await db_client.complete_quest_atomic(test_quest.questId)
        assert success is True
        
        # Verify completion
        completed_quest = await db_client.get_quest(test_quest.questId)
        assert completed_quest.status == QuestStatus.COMPLETE
        assert completed_quest.completedAt is not None
    
    @pytest.mark.asyncio
    async def test_complete_quest_atomic_wrong_status(self, db_client, test_quest):
        """Test completing quest in wrong status"""
        # Try to complete an OPEN quest
        success = await db_client.complete_quest_atomic(test_quest.questId)
        assert success is False


class TestUserManagement:
    """Test user management operations"""
    
    @pytest.mark.asyncio
    async def test_create_and_get_user(self, db_client):
        """Test creating and retrieving a user"""
        user = User(
            userId="new-user-456",
            username="newuser@example.com",
            reputation=0,
            experience=0,
            questCreationPoints=500,
            createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
        )
        
        await db_client.create_user(user)
        
        # Get user
        retrieved_user = await db_client.get_user(user.userId)
        assert retrieved_user is not None
        assert retrieved_user.userId == user.userId
        assert retrieved_user.username == user.username
        assert retrieved_user.questCreationPoints == 500
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db_client):
        """Test getting a user that doesn't exist"""
        result = await db_client.get_user("nonexistent-user-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_deduct_quest_creation_points_success(self, db_client, test_user):
        """Test successfully deducting quest creation points"""
        initial_points = test_user.questCreationPoints
        
        success = await db_client.deduct_quest_creation_points(test_user.userId)
        assert success is True
        
        # Verify points were deducted (default is 1 point)
        updated_user = await db_client.get_user(test_user.userId)
        assert updated_user.questCreationPoints == initial_points - 1
    
    @pytest.mark.asyncio
    async def test_deduct_quest_creation_points_insufficient(self, db_client):
        """Test deducting points with insufficient balance"""
        # Create user with 0 points
        user = User(
            userId="poor-user",
            username="poor@example.com",
            reputation=0,
            experience=0,
            questCreationPoints=0,
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc)
        )
        await db_client.create_user(user)
        
        # Try to deduct 1 point (default)
        success = await db_client.deduct_quest_creation_points(user.userId)
        assert success is False
        
        # Verify points weren't changed
        updated_user = await db_client.get_user(user.userId)
        assert updated_user.questCreationPoints == 0


class TestQueryOperations:
    """Test query operations"""
    
    @pytest.mark.asyncio
    async def test_list_quests_with_status(self, db_client, test_user):
        """Test listing quests by status using GSI"""
        # Create multiple quests with different statuses
        open_quest = Quest(
            questId="quest-open-1",
            creatorId=test_user.userId,
            title="Open Quest",
            description="An open quest",
            rewardXp=50,
            rewardReputation=5,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
            attestations=[]
        )
        claimed_quest = Quest(
            questId="quest-claimed-1",
            creatorId=test_user.userId,
            title="Claimed Quest",
            description="A claimed quest",
            rewardXp=50,
            rewardReputation=5,
            status=QuestStatus.CLAIMED,
            performerId="performer-123",
            createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        await db_client.create_quest(open_quest)
        await db_client.create_quest(claimed_quest)
        
        # List only OPEN quests
        open_quests = await db_client.list_quests(status=QuestStatus.OPEN)
        assert len(open_quests) >= 1
        assert all(q.status == QuestStatus.OPEN for q in open_quests)
    
    @pytest.mark.asyncio
    async def test_list_quests_without_status(self, db_client):
        """Test listing all quests using scan"""
        # This should use scan instead of query
        all_quests = await db_client.list_quests()
        assert isinstance(all_quests, list)
    
    @pytest.mark.asyncio
    async def test_list_quests_gsi_fallback(self, db_client):
        """Test fallback to scan when GSI doesn't exist"""
        # Create a mock client
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.query.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'Query'
        )
        # The scan should work normally
        mock_dynamodb_client.scan.return_value = {'Items': []}
        
        # Create a mock async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should fall back to scan
            quests = await db_client.list_quests(status=QuestStatus.OPEN)
            assert isinstance(quests, list)
    
    @pytest.mark.asyncio
    async def test_get_user_created_quests(self, db_client, test_user):
        """Test getting quests created by a user"""
        # Create a quest for the user
        quest = Quest(
            questId="user-quest-1",
            creatorId=test_user.userId,
            title="User's Quest",
            description="A quest created by the user",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
            attestations=[]
        )
        await db_client.create_quest(quest)
        
        # Get user's created quests
        created_quests = await db_client.get_user_created_quests(test_user.userId)
        assert len(created_quests) >= 1
        assert all(q.creatorId == test_user.userId for q in created_quests)
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self, db_client, test_user):
        """Test getting user stats"""
        stats = await db_client.get_user_stats(test_user.userId)
        
        assert stats is not None
        assert 'questsCreated' in stats
        assert 'questsCompleted' in stats
        assert isinstance(stats['questsCreated'], int)
        assert isinstance(stats['questsCompleted'], int)
        assert stats['questsCreated'] >= 0
        assert stats['questsCompleted'] >= 0


class TestRewardsAndEdgeCases:
    """Test reward operations and edge cases"""
    
    @pytest.mark.asyncio
    async def test_award_rewards_success(self, db_client, test_user):
        """Test successfully awarding rewards"""
        initial_xp = test_user.experience
        initial_rep = test_user.reputation
        
        await db_client.award_rewards(test_user.userId, xp=50, reputation=5)
        
        # Verify rewards were added
        updated_user = await db_client.get_user(test_user.userId)
        assert updated_user.experience == initial_xp + 50
        assert updated_user.reputation == initial_rep + 5
    
    @pytest.mark.asyncio
    async def test_award_rewards_handles_error(self, db_client, test_user):
        """Test award_rewards handles errors and tracks failures"""
        # Create a mock client
        mock_dynamodb_client = AsyncMock()
        mock_dynamodb_client.update_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError'}},
            'UpdateItem'
        )
        
        # Create a mock async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_dynamodb_client
        
        with patch.object(db_client, 'get_resource', return_value=mock_context_manager):
            # Should raise the error
            with pytest.raises(ClientError):
                await db_client.award_rewards(test_user.userId, xp=50, reputation=5)
    
    @pytest.mark.asyncio
    async def test_delete_quest_atomic_success(self, db_client, test_quest):
        """Test successfully deleting a quest"""
        success = await db_client.delete_quest_atomic(
            test_quest.questId,
            test_quest.creatorId
        )
        assert success is True
        
        # Verify quest was deleted
        deleted_quest = await db_client.get_quest(test_quest.questId)
        assert deleted_quest is None
    
    @pytest.mark.asyncio
    async def test_delete_quest_atomic_wrong_user(self, db_client, test_quest):
        """Test deleting quest by non-creator"""
        wrong_user = "not-the-creator"
        
        success = await db_client.delete_quest_atomic(
            test_quest.questId,
            wrong_user
        )
        assert success is False
        
        # Verify quest still exists
        quest = await db_client.get_quest(test_quest.questId)
        assert quest is not None
    
    @pytest.mark.asyncio
    async def test_delete_quest_atomic_wrong_status(self, db_client, test_quest):
        """Test deleting quest in wrong status"""
        # Claim the quest first
        await db_client.claim_quest_atomic(test_quest.questId, "performer-123")
        
        # Try to delete a CLAIMED quest
        success = await db_client.delete_quest_atomic(
            test_quest.questId,
            test_quest.creatorId
        )
        assert success is False
        
        # Verify quest still exists
        quest = await db_client.get_quest(test_quest.questId)
        assert quest is not None
        assert quest.status == QuestStatus.CLAIMED