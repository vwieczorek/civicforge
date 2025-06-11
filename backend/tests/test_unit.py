"""
Simple working tests to boost coverage to 70%
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from src.models import Quest, QuestStatus, User, QuestCreate, QuestSubmission
from src.state_machine import QuestStateMachine
from src.signature import create_attestation_message
from src.feature_flags import FeatureFlagManager, FeatureFlag


def test_signature_create_message():
    """Test signature message creation."""
    result = create_attestation_message("quest123", "user456", "requestor")
    expected = (
        "I am attesting to the completion of CivicForge Quest.\n"
        "Quest ID: quest123\n"
        "My User ID: user456\n"
        "My Role: requestor"
    )
    assert result == expected


def test_state_machine_can_user_claim():
    """Test state machine user claim validation."""
    quest = Quest(
        questId="q1",
        creatorId="user1",
        title="Test",
        description="Test",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.OPEN,
        createdAt=datetime.utcnow()
    )
    
    # Creator cannot claim own quest
    assert QuestStateMachine.can_user_claim(quest, "user1") is False
    
    # Different user can claim
    assert QuestStateMachine.can_user_claim(quest, "user2") is True


def test_state_machine_can_user_submit():
    """Test state machine user submit validation."""
    quest = Quest(
        questId="q1",
        creatorId="user1",
        title="Test",
        description="Test",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.CLAIMED,
        performerId="user2",
        createdAt=datetime.utcnow()
    )
    
    # Performer can submit
    assert QuestStateMachine.can_user_submit(quest, "user2") is True
    
    # Non-performer cannot submit
    assert QuestStateMachine.can_user_submit(quest, "user3") is False


def test_state_machine_get_user_role():
    """Test getting user role."""
    quest = Quest(
        questId="q1",
        creatorId="user1",
        title="Test",
        description="Test", 
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.CLAIMED,
        performerId="user2",
        createdAt=datetime.utcnow()
    )
    
    assert QuestStateMachine.get_user_role(quest, "user1") == "requestor"
    assert QuestStateMachine.get_user_role(quest, "user2") == "performer"
    assert QuestStateMachine.get_user_role(quest, "user3") is None


def test_feature_flags_percentage_rollout():
    """Test feature flags percentage rollout."""
    flags = FeatureFlagManager()
    
    # Test with known user ID
    user_id = "test_user_123"
    user_hash = hash(user_id) % 100
    
    # Should be consistent
    assert flags._is_in_rollout_percentage(user_id, user_hash + 1) is True
    assert flags._is_in_rollout_percentage(user_id, user_hash - 1) is False
    
    # Edge cases
    assert flags._is_in_rollout_percentage(None, 50) is False
    assert flags._is_in_rollout_percentage(user_id, 0) is False
    assert flags._is_in_rollout_percentage(user_id, 100) is True


def test_feature_flags_is_enabled():
    """Test feature flag enabled check."""
    flags = FeatureFlagManager()
    
    # Test environment variable based flags
    with patch.dict('os.environ', {'FF_REWARD_DISTRIBUTION': 'true'}):
        assert flags.is_enabled(FeatureFlag.REWARD_DISTRIBUTION) is True
    
    with patch.dict('os.environ', {'FF_REWARD_DISTRIBUTION': 'false'}):
        assert flags.is_enabled(FeatureFlag.REWARD_DISTRIBUTION) is False


def test_feature_flags_internal_users():
    """Test internal user feature flags."""
    flags = FeatureFlagManager()
    
    with patch.dict('os.environ', {
        'FF_DISPUTE_RESOLUTION': 'internal',
        'INTERNAL_USERS': 'admin1,admin2'
    }):
        assert flags.is_enabled(FeatureFlag.DISPUTE_RESOLUTION, "admin1") is True
        assert flags.is_enabled(FeatureFlag.DISPUTE_RESOLUTION, "user123") is False


def test_db_serialization():
    """Test database serialization/deserialization."""
    from src.db import DynamoDBClient
    
    client = DynamoDBClient()
    
    test_data = {
        'string_val': 'test',
        'int_val': 42,
        'bool_val': True,
        'null_val': None,
        'list_val': [1, 'two'],
        'set_val': {'item1', 'item2'}
    }
    
    serialized = client._serialize_item(test_data)
    deserialized = client._deserialize_item(serialized)
    
    assert deserialized['string_val'] == 'test'
    assert deserialized['int_val'] == 42
    assert deserialized['bool_val'] is True
    assert deserialized['null_val'] is None
    assert deserialized['set_val'] == {'item1', 'item2'}


def test_quest_create_validation():
    """Test QuestCreate validation with clean data."""
    quest_data = {
        "title": "Clean Test Quest",
        "description": "Clean description without HTML",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    quest = QuestCreate(**quest_data)
    assert quest.title == "Clean Test Quest"
    assert quest.description == "Clean description without HTML"


def test_quest_submission_validation():
    """Test QuestSubmission validation with clean data."""
    submission_data = {
        "submissionText": "Clean submission text without HTML"
    }
    
    submission = QuestSubmission(**submission_data)
    assert submission.submissionText == "Clean submission text without HTML"


@patch('src.signature.Account.recover_message')
@patch('src.signature.encode_defunct')
def test_signature_verification(mock_encode, mock_recover):
    """Test signature verification logic."""
    from src.signature import verify_attestation_signature, extract_address_from_signature
    
    mock_encode.return_value = "encoded_message"
    mock_recover.return_value = "0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3"
    
    # Test successful verification
    result = verify_attestation_signature(
        "quest123", "user456", "requestor", 
        "0x1234567890abcdef", "0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3"
    )
    assert result is True
    
    # Test address extraction
    address = extract_address_from_signature(
        "quest123", "user456", "requestor", "0x1234567890abcdef"
    )
    assert address == "0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3"


@patch('src.signature.Account.recover_message', side_effect=Exception("Test error"))
def test_signature_verification_error_handling(mock_recover):
    """Test signature verification error handling."""
    from src.signature import verify_attestation_signature, extract_address_from_signature
    
    with patch('builtins.print') as mock_print:
        result = verify_attestation_signature(
            "quest123", "user456", "requestor",
            "0x1234567890abcdef", "0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3"
        )
        assert result is False
        mock_print.assert_called_once()
    
    with patch('builtins.print') as mock_print:
        address = extract_address_from_signature(
            "quest123", "user456", "requestor", "0x1234567890abcdef"
        )
        assert address is None
        mock_print.assert_called_once()


async def test_auth_functions():
    """Test auth module functions."""
    from src.auth import verify_token, get_current_user_claims, get_current_user_id
    import jwt
    from fastapi import HTTPException
    
    # Test expired token
    with patch('src.auth.jwt.get_unverified_header') as mock_header, \
         patch('src.auth.get_cognito_keys') as mock_keys, \
         patch('src.auth.jwt.decode', side_effect=jwt.ExpiredSignatureError("Expired")):
        
        mock_header.return_value = {"kid": "test-key"}
        mock_keys.return_value = {"keys": [
            {"kid": "test-key", "kty": "RSA", "use": "sig", "alg": "RS256", "n": "test", "e": "AQAB"}
        ]}
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token("expired-token")
        assert exc_info.value.status_code == 401
    
    # Test invalid token
    with patch('src.auth.jwt.get_unverified_header') as mock_header, \
         patch('src.auth.get_cognito_keys') as mock_keys, \
         patch('src.auth.jwt.decode', side_effect=jwt.InvalidTokenError("Invalid")):
        
        mock_header.return_value = {"kid": "test-key"}
        mock_keys.return_value = {"keys": [
            {"kid": "test-key", "kty": "RSA", "use": "sig", "alg": "RS256", "n": "test", "e": "AQAB"}
        ]}
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid-token")
        assert exc_info.value.status_code == 401
    
    # Test valid token claims
    with patch('src.auth.verify_token', return_value={"sub": "user123", "email": "test@example.com"}):
        claims = await get_current_user_claims("Bearer valid-token")
        assert claims["sub"] == "user123"
        
        user_id = await get_current_user_id("Bearer valid-token")
        assert user_id == "user123"


def test_state_machine_validation_fixed():
    """Test state machine validation logic - FIXED argument order."""
    quest = Quest(
        questId="q1",
        creatorId="user1",
        title="Test Quest",
        description="Test description for quest",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.OPEN,
        createdAt=datetime.utcnow()
    )
    
    # Valid transition should pass - CORRECT argument order: quest, user_id, from_status, to_status
    is_valid, error = QuestStateMachine.validate_transition(
        quest, "user2", QuestStatus.OPEN, QuestStatus.CLAIMED
    )
    assert is_valid is True
    assert error is None
    
    # Test dispute transitions
    quest.status = QuestStatus.SUBMITTED
    quest.performerId = "user2"
    assert QuestStateMachine.can_user_dispute(quest, "user1") is True


def test_state_machine_attestation():
    """Test state machine attestation logic."""
    from src.models import Attestation
    
    quest = Quest(
        questId="q1",
        creatorId="user1",
        title="Test Quest",
        description="Test description for quest",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.SUBMITTED,
        performerId="user2",
        createdAt=datetime.utcnow(),
        attestations=[]
    )
    
    # Can attest if not already attested
    assert QuestStateMachine.can_user_attest(quest, "user1") is True
    
    # Cannot attest if already attested - add attestation to test this
    attestation = Attestation(
        user_id="user1",
        role="requestor",
        attested_at=datetime.utcnow()
    )
    quest.attestations.append(attestation)
    assert QuestStateMachine.can_user_attest(quest, "user1") is False


def test_state_machine_can_user_dispute():
    """Test state machine dispute logic."""
    quest = Quest(
        questId="q1",
        creatorId="user1",
        title="Test Quest",
        description="Test description for quest",
        rewardXp=100,
        rewardReputation=10,
        status=QuestStatus.SUBMITTED,
        performerId="user2",
        createdAt=datetime.utcnow()
    )
    
    # Creator can dispute
    assert QuestStateMachine.can_user_dispute(quest, "user1") is True
    
    # Performer can dispute
    assert QuestStateMachine.can_user_dispute(quest, "user2") is True
    
    # Other user cannot dispute
    assert QuestStateMachine.can_user_dispute(quest, "user3") is False
    
    # Cannot dispute if not in SUBMITTED status
    quest.status = QuestStatus.OPEN
    assert QuestStateMachine.can_user_dispute(quest, "user1") is False


def test_feature_flags_get_all_flags():
    """Test feature flags get_all_flags method."""
    flags = FeatureFlagManager()
    
    with patch.dict('os.environ', {
        'FF_REWARD_DISTRIBUTION': 'false',
        'FF_SIGNATURE_ATTESTATION': 'true',
        'FF_DISPUTE_RESOLUTION': 'internal',
        'INTERNAL_USERS': 'admin1,admin2'
    }):
        all_flags = flags.get_all_flags()
        assert isinstance(all_flags, dict)
        assert "reward_distribution" in all_flags
        assert "signature_attestation" in all_flags
        assert "dispute_resolution" in all_flags


def test_models_validation_patterns():
    """Test model validation patterns."""
    # Test valid inputs (no HTML)
    valid_inputs = [
        "Normal text",
        "Text with safe content",
        "Numbers 123 and symbols !@#",
        "Safe punctuation and spaces"
    ]
    
    for safe_input in valid_inputs:
        quest_data = {
            "title": f"Title: {safe_input}",
            "description": f"Description with {safe_input} and more content to meet length requirements",
            "rewardXp": 100,
            "rewardReputation": 10
        }
        
        # Should not raise an exception
        quest = QuestCreate(**quest_data)
        assert safe_input in quest.title or safe_input in quest.description
    
    # Test that HTML inputs are rejected by validation
    with pytest.raises(ValueError):
        QuestCreate(
            title="Title with <script>alert('xss')</script> content",
            description="Safe description without HTML content that meets length requirements",
            rewardXp=100,
            rewardReputation=10
        )


def test_additional_db_serialization_edge_cases():
    """Test additional database serialization edge cases."""
    from src.db import DynamoDBClient
    
    client = DynamoDBClient()
    
    # Test edge cases
    edge_case_data = {
        'empty_string': '',
        'zero_int': 0,
        'false_bool': False,
        'empty_list': [],
        'empty_dict': {},
        'nested_structure': {
            'inner_list': [1, 2, {'nested_dict': True}],
            'inner_set': {'a', 'b', 'c'}
        }
    }
    
    serialized = client._serialize_item(edge_case_data)
    deserialized = client._deserialize_item(serialized)
    
    assert deserialized['empty_string'] == ''
    assert deserialized['zero_int'] == 0
    assert deserialized['false_bool'] is False
    assert deserialized['empty_list'] == []
    assert deserialized['empty_dict'] == {}
    assert deserialized['nested_structure']['inner_set'] == {'a', 'b', 'c'}


def test_signature_edge_cases():
    """Test signature verification edge cases."""
    from src.signature import create_attestation_message
    
    # Test with various inputs
    edge_cases = [
        ("", "", ""),
        ("quest-with-dashes", "user_with_underscores", "requestor"),
        ("quest123", "user456", "performer"),
        ("very-long-quest-id-with-many-characters", "user", "requestor")
    ]
    
    for quest_id, user_id, role in edge_cases:
        result = create_attestation_message(quest_id, user_id, role)
        
        # Should always return a string
        assert isinstance(result, str)
        
        # Should contain the expected format
        expected_parts = [
            "I am attesting to the completion of CivicForge Quest.",
            f"Quest ID: {quest_id}",
            f"My User ID: {user_id}",
            f"My Role: {role}"
        ]
        
        for part in expected_parts:
            assert part in result