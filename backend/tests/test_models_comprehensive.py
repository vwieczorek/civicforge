"""
Comprehensive unit tests for models.py - high coverage gains without mocking
"""

import pytest
from datetime import datetime
from src.models import Quest, QuestDB, QuestCreate, QuestSubmission, User, Attestation, QuestStatus


def test_quest_computed_properties_empty():
    """Test Quest computed properties with no attestations."""
    quest = Quest(
        questId="q1", 
        creatorId="c1", 
        title="Test Quest", 
        description="Test description for quest",
        createdAt=datetime.utcnow()
    )
    assert quest.attester_ids == []
    assert quest.has_requestor_attestation is False
    assert quest.has_performer_attestation is False


def test_quest_computed_properties_requestor_attestation():
    """Test Quest computed properties with requestor attestation."""
    quest = Quest(
        questId="q1", 
        creatorId="c1", 
        title="Test Quest", 
        description="Test description for quest",
        createdAt=datetime.utcnow()
    )
    
    # Add requestor attestation
    quest.attestations.append(
        Attestation(user_id="c1", role="requestor", attested_at=datetime.utcnow())
    )
    assert quest.attester_ids == ["c1"]
    assert quest.has_requestor_attestation is True
    assert quest.has_performer_attestation is False


def test_quest_computed_properties_dual_attestation():
    """Test Quest computed properties with dual attestation."""
    quest = Quest(
        questId="q1", 
        creatorId="c1", 
        title="Test Quest", 
        description="Test description for quest",
        createdAt=datetime.utcnow()
    )
    
    # Add both attestations
    quest.attestations.append(
        Attestation(user_id="c1", role="requestor", attested_at=datetime.utcnow())
    )
    quest.attestations.append(
        Attestation(user_id="p1", role="performer", attested_at=datetime.utcnow())
    )
    assert sorted(quest.attester_ids) == ["c1", "p1"]
    assert quest.has_requestor_attestation is True
    assert quest.has_performer_attestation is True


def test_questdb_model_validator_no_attestations():
    """Test QuestDB model validator with no attestations."""
    quest_data = {
        "questId": "q1", 
        "creatorId": "c1", 
        "title": "Test Quest", 
        "description": "Test description for quest",
        "createdAt": datetime.utcnow()
    }
    db_quest = QuestDB(**quest_data)
    assert db_quest.attesterIds is None
    assert db_quest.hasRequestorAttestation is False
    assert db_quest.hasPerformerAttestation is False


def test_questdb_model_validator_with_attestations():
    """Test QuestDB model validator with attestations."""
    quest_data = {
        "questId": "q1", 
        "creatorId": "c1", 
        "title": "Test Quest", 
        "description": "Test description for quest",
        "createdAt": datetime.utcnow(),
        "attestations": [
            {"user_id": "c1", "role": "requestor", "attested_at": datetime.utcnow()},
            {"user_id": "p1", "role": "performer", "attested_at": datetime.utcnow()}
        ]
    }
    db_quest = QuestDB(**quest_data)
    assert db_quest.attesterIds == {"c1", "p1"}
    assert db_quest.hasRequestorAttestation is True
    assert db_quest.hasPerformerAttestation is True


def test_quest_create_validation_valid_data():
    """Test QuestCreate validation with valid data."""
    quest_data = {
        "title": "Valid Test Quest Title",
        "description": "This is a valid description that is long enough to pass validation requirements",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    quest = QuestCreate(**quest_data)
    assert quest.title == "Valid Test Quest Title"
    assert "valid description" in quest.description


def test_quest_create_validation_sanitizes_html():
    """Test QuestCreate sanitizes HTML content using bleach."""
    # The sanitizer should remove malicious scripts but keep safe content
    quest = QuestCreate(
        title="Title with <script>alert('xss')</script> content",
        description="Description with <p>safe content</p> and <script>alert('xss')</script> malicious content that meets minimum length requirements",
        rewardXp=100,
        rewardReputation=10
    )
    
    # Script tags should be removed
    assert "<script>" not in quest.title
    assert "alert('xss')" in quest.title  # The text content remains
    assert "<script>" not in quest.description
    assert "alert('xss')" in quest.description  # The text content remains
    assert "<p>safe content</p>" in quest.description  # Safe tags are kept


def test_quest_create_validation_title_too_short():
    """Test QuestCreate validation fails with short title."""
    with pytest.raises(ValueError):
        QuestCreate(
            title="Hi",
            description="This description is long enough to pass validation requirements",
            rewardXp=100,
            rewardReputation=10
        )


def test_quest_create_validation_description_too_short():
    """Test QuestCreate validation fails with short description."""
    with pytest.raises(ValueError):
        QuestCreate(
            title="Valid Quest Title",
            description="Too short",
            rewardXp=100,
            rewardReputation=10
        )


def test_quest_create_validation_reward_bounds():
    """Test QuestCreate validation enforces reward bounds."""
    # XP too low
    with pytest.raises(ValueError):
        QuestCreate(
            title="Valid Quest Title",
            description="This description is long enough to pass validation requirements",
            rewardXp=5,  # Below minimum of 10
            rewardReputation=10
        )
    
    # XP too high
    with pytest.raises(ValueError):
        QuestCreate(
            title="Valid Quest Title",
            description="This description is long enough to pass validation requirements",
            rewardXp=1500,  # Above maximum of 1000
            rewardReputation=10
        )
    
    # Reputation too low
    with pytest.raises(ValueError):
        QuestCreate(
            title="Valid Quest Title",
            description="This description is long enough to pass validation requirements",
            rewardXp=100,
            rewardReputation=0  # Below minimum of 1
        )
    
    # Reputation too high
    with pytest.raises(ValueError):
        QuestCreate(
            title="Valid Quest Title",
            description="This description is long enough to pass validation requirements",
            rewardXp=100,
            rewardReputation=150  # Above maximum of 100
        )


def test_quest_submission_validation_valid():
    """Test QuestSubmission validation with valid data."""
    submission_data = {
        "submissionText": "This is a valid submission with enough content to describe completed work"
    }
    submission = QuestSubmission(**submission_data)
    assert "valid submission" in submission.submissionText


def test_quest_submission_validation_sanitizes_html():
    """Test QuestSubmission sanitizes HTML content using bleach."""
    # The sanitizer should remove malicious scripts but keep safe content
    submission = QuestSubmission(
        submissionText="Work completed with <b>bold text</b> and <script>alert('xss')</script> and other formatting"
    )
    
    # Script tags should be removed, safe tags kept
    assert "<script>" not in submission.submissionText
    assert "alert('xss')" in submission.submissionText  # Text content remains
    assert "<b>bold text</b>" in submission.submissionText  # Safe tags are kept


def test_user_model_defaults():
    """Test User model default values."""
    user = User(
        userId="user123",
        username="testuser",
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    assert user.walletAddress is None
    assert user.reputation == 0
    assert user.experience == 0
    assert user.questCreationPoints == 10


def test_user_model_with_values():
    """Test User model with all values set."""
    now = datetime.utcnow()
    user = User(
        userId="user123",
        username="testuser",
        walletAddress="0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3",
        reputation=150,
        experience=2500,
        questCreationPoints=5,
        createdAt=now,
        updatedAt=now
    )
    assert user.walletAddress == "0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3"
    assert user.reputation == 150
    assert user.experience == 2500
    assert user.questCreationPoints == 5


def test_attestation_model():
    """Test Attestation model."""
    now = datetime.utcnow()
    attestation = Attestation(
        user_id="user123",
        role="requestor",
        attested_at=now,
        signature="0x1234567890abcdef"
    )
    assert attestation.user_id == "user123"
    assert attestation.role == "requestor"
    assert attestation.attested_at == now
    assert attestation.signature == "0x1234567890abcdef"


def test_attestation_model_no_signature():
    """Test Attestation model without signature."""
    now = datetime.utcnow()
    attestation = Attestation(
        user_id="user123",
        role="performer",
        attested_at=now
    )
    assert attestation.user_id == "user123"
    assert attestation.role == "performer"
    assert attestation.signature is None


def test_quest_status_enum():
    """Test QuestStatus enum values."""
    assert QuestStatus.OPEN == "OPEN"
    assert QuestStatus.CLAIMED == "CLAIMED"
    assert QuestStatus.SUBMITTED == "SUBMITTED"
    assert QuestStatus.COMPLETE == "COMPLETE"
    assert QuestStatus.DISPUTED == "DISPUTED"
    assert QuestStatus.EXPIRED == "EXPIRED"


def test_quest_model_defaults():
    """Test Quest model default values."""
    quest = Quest(
        questId="q1",
        creatorId="creator1",
        title="Test Quest",
        description="Test description for quest",
        createdAt=datetime.utcnow()
    )
    assert quest.status == QuestStatus.OPEN
    assert quest.performerId is None
    assert quest.rewardXp == 100
    assert quest.rewardReputation == 10
    assert quest.attestations == []
    assert quest.claimedAt is None
    assert quest.submittedAt is None
    assert quest.completedAt is None
    assert quest.submissionText is None
    assert quest.dispute_reason is None
    assert quest.ttl is None


def test_quest_model_all_fields():
    """Test Quest model with all fields set."""
    now = datetime.utcnow()
    attestations = [
        Attestation(user_id="creator1", role="requestor", attested_at=now),
        Attestation(user_id="performer1", role="performer", attested_at=now)
    ]
    
    quest = Quest(
        questId="q1",
        creatorId="creator1",
        title="Complete Test Quest",
        description="Comprehensive test quest description",
        status=QuestStatus.COMPLETE,
        performerId="performer1",
        rewardXp=250,
        rewardReputation=25,
        attestations=attestations,
        createdAt=now,
        claimedAt=now,
        submittedAt=now,
        completedAt=now,
        updatedAt=now,
        submissionText="Work has been completed successfully",
        dispute_reason=None,
        ttl=1640995200
    )
    
    assert quest.status == QuestStatus.COMPLETE
    assert quest.performerId == "performer1"
    assert quest.rewardXp == 250
    assert quest.rewardReputation == 25
    assert len(quest.attestations) == 2
    assert quest.submissionText == "Work has been completed successfully"
    assert quest.ttl == 1640995200


def test_quest_model_disputed():
    """Test Quest model in disputed state."""
    quest = Quest(
        questId="q1",
        creatorId="creator1",
        title="Disputed Quest",
        description="Quest that ended up in dispute",
        status=QuestStatus.DISPUTED,
        performerId="performer1",
        createdAt=datetime.utcnow(),
        dispute_reason="Work quality did not meet requirements"
    )
    
    assert quest.status == QuestStatus.DISPUTED
    assert quest.dispute_reason == "Work quality did not meet requirements"


def test_quest_field_constraints():
    """Test Quest model field constraints."""
    # Test reward XP bounds
    quest = Quest(
        questId="q1",
        creatorId="creator1", 
        title="Test Quest",
        description="Test description",
        rewardXp=10,  # Minimum allowed
        rewardReputation=1,  # Minimum allowed
        createdAt=datetime.utcnow()
    )
    assert quest.rewardXp == 10
    assert quest.rewardReputation == 1
    
    # Test maximum bounds
    quest = Quest(
        questId="q1",
        creatorId="creator1",
        title="Test Quest", 
        description="Test description",
        rewardXp=1000,  # Maximum allowed
        rewardReputation=100,  # Maximum allowed
        createdAt=datetime.utcnow()
    )
    assert quest.rewardXp == 1000
    assert quest.rewardReputation == 100