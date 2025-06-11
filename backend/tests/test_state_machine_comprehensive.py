"""
Comprehensive unit tests for QuestStateMachine - high coverage gains without mocking
"""

import pytest
from datetime import datetime
from src.models import Quest, QuestStatus, Attestation
from src.state_machine import QuestStateMachine


# Test Data Fixtures
@pytest.fixture
def open_quest():
    return Quest(
        questId="q1", 
        creatorId="creator1", 
        title="Test Quest", 
        description="Test description for quest",
        createdAt=datetime.utcnow(), 
        status=QuestStatus.OPEN
    )


@pytest.fixture
def claimed_quest(open_quest):
    open_quest.status = QuestStatus.CLAIMED
    open_quest.performerId = "performer1"
    return open_quest


@pytest.fixture
def submitted_quest(claimed_quest):
    claimed_quest.status = QuestStatus.SUBMITTED
    return claimed_quest


# Tests for validate_transition
def test_validate_transition_claim_success(open_quest):
    """Test valid claim transition."""
    is_valid, err = QuestStateMachine.validate_transition(
        open_quest, "new_user", QuestStatus.OPEN, QuestStatus.CLAIMED
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_claim_creator_cannot_claim_own(open_quest):
    """Test that creator cannot claim their own quest."""
    is_valid, err = QuestStateMachine.validate_transition(
        open_quest, "creator1", QuestStatus.OPEN, QuestStatus.CLAIMED
    )
    assert is_valid is False
    assert "cannot claim their own quest" in err


def test_validate_transition_claim_already_claimed(open_quest):
    """Test claiming already claimed quest fails."""
    open_quest.performerId = "another_user"
    is_valid, err = QuestStateMachine.validate_transition(
        open_quest, "new_user", QuestStatus.OPEN, QuestStatus.CLAIMED
    )
    assert is_valid is False
    assert "Quest already claimed" in err


def test_validate_transition_unclaim_success(claimed_quest):
    """Test valid unclaim transition."""
    is_valid, err = QuestStateMachine.validate_transition(
        claimed_quest, "performer1", QuestStatus.CLAIMED, QuestStatus.OPEN
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_unclaim_only_performer_can_unclaim(claimed_quest):
    """Test that only performer can unclaim."""
    is_valid, err = QuestStateMachine.validate_transition(
        claimed_quest, "creator1", QuestStatus.CLAIMED, QuestStatus.OPEN
    )
    assert is_valid is False
    assert "Only performer can unclaim" in err


def test_validate_transition_submit_success(claimed_quest):
    """Test valid submit transition."""
    is_valid, err = QuestStateMachine.validate_transition(
        claimed_quest, "performer1", QuestStatus.CLAIMED, QuestStatus.SUBMITTED
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_submit_only_performer_can_submit(claimed_quest):
    """Test that only performer can submit."""
    is_valid, err = QuestStateMachine.validate_transition(
        claimed_quest, "creator1", QuestStatus.CLAIMED, QuestStatus.SUBMITTED
    )
    assert is_valid is False
    assert "Only performer can submit" in err


def test_validate_transition_complete_no_attestations(submitted_quest):
    """Test completion fails without attestations."""
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "any_user", QuestStatus.SUBMITTED, QuestStatus.COMPLETE
    )
    assert is_valid is False
    assert "Requires attestation" in err


def test_validate_transition_complete_single_attestation(submitted_quest):
    """Test completion fails with only one attestation."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "any_user", QuestStatus.SUBMITTED, QuestStatus.COMPLETE
    )
    assert is_valid is False
    assert "Requires attestation" in err


def test_validate_transition_complete_dual_attestation_success(submitted_quest):
    """Test completion succeeds with dual attestation."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    submitted_quest.attestations.append(
        Attestation(user_id="performer1", role="performer", attested_at=datetime.utcnow())
    )
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "any_user", QuestStatus.SUBMITTED, QuestStatus.COMPLETE
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_dispute_creator_can_dispute(submitted_quest):
    """Test that creator can dispute."""
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "creator1", QuestStatus.SUBMITTED, QuestStatus.DISPUTED
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_dispute_performer_can_dispute(submitted_quest):
    """Test that performer can dispute."""
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "performer1", QuestStatus.SUBMITTED, QuestStatus.DISPUTED
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_dispute_other_user_cannot_dispute(submitted_quest):
    """Test that other users cannot dispute."""
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "other_user", QuestStatus.SUBMITTED, QuestStatus.DISPUTED
    )
    assert is_valid is False
    assert "Only involved parties can dispute" in err


def test_validate_transition_invalid_path(open_quest):
    """Test invalid transition path fails."""
    is_valid, err = QuestStateMachine.validate_transition(
        open_quest, "any_user", QuestStatus.OPEN, QuestStatus.SUBMITTED
    )
    assert is_valid is False
    assert "Invalid transition" in err


def test_validate_transition_wrong_from_status(open_quest):
    """Test transition fails when quest is not in expected from_status."""
    is_valid, err = QuestStateMachine.validate_transition(
        open_quest, "any_user", QuestStatus.CLAIMED, QuestStatus.SUBMITTED
    )
    assert is_valid is False
    assert "Quest is not in expected state" in err


# Tests for can_user_attest
def test_can_user_attest_creator_can_attest(submitted_quest):
    """Test that creator can attest."""
    assert QuestStateMachine.can_user_attest(submitted_quest, "creator1") is True


def test_can_user_attest_performer_can_attest(submitted_quest):
    """Test that performer can attest."""
    assert QuestStateMachine.can_user_attest(submitted_quest, "performer1") is True


def test_can_user_attest_quest_not_submitted(submitted_quest):
    """Test that user cannot attest if quest not in SUBMITTED state."""
    submitted_quest.status = QuestStatus.CLAIMED
    assert QuestStateMachine.can_user_attest(submitted_quest, "creator1") is False


def test_can_user_attest_user_not_participant(submitted_quest):
    """Test that non-participants cannot attest."""
    assert QuestStateMachine.can_user_attest(submitted_quest, "other_user") is False


def test_can_user_attest_user_already_attested(submitted_quest):
    """Test that user cannot attest twice."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    assert QuestStateMachine.can_user_attest(submitted_quest, "creator1") is False


# Tests for is_ready_for_completion
def test_is_ready_for_completion_not_submitted(submitted_quest):
    """Test that quest not ready if not in SUBMITTED state."""
    submitted_quest.status = QuestStatus.CLAIMED
    assert QuestStateMachine.is_ready_for_completion(submitted_quest) is False


def test_is_ready_for_completion_no_attestations(submitted_quest):
    """Test that quest not ready without attestations."""
    assert QuestStateMachine.is_ready_for_completion(submitted_quest) is False


def test_is_ready_for_completion_one_attestation(submitted_quest):
    """Test that quest not ready with only one attestation."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    assert QuestStateMachine.is_ready_for_completion(submitted_quest) is False


def test_is_ready_for_completion_dual_attestation(submitted_quest):
    """Test that quest ready with dual attestation."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    submitted_quest.attestations.append(
        Attestation(user_id="performer1", role="performer", attested_at=datetime.utcnow())
    )
    assert QuestStateMachine.is_ready_for_completion(submitted_quest) is True


# Tests for can_user_dispute
def test_can_user_dispute_creator_can_dispute(submitted_quest):
    """Test that creator can dispute."""
    assert QuestStateMachine.can_user_dispute(submitted_quest, "creator1") is True


def test_can_user_dispute_performer_can_dispute(submitted_quest):
    """Test that performer can dispute."""
    assert QuestStateMachine.can_user_dispute(submitted_quest, "performer1") is True


def test_can_user_dispute_other_user_cannot_dispute(submitted_quest):
    """Test that non-participants cannot dispute."""
    assert QuestStateMachine.can_user_dispute(submitted_quest, "other_user") is False


def test_can_user_dispute_wrong_status(open_quest):
    """Test that user cannot dispute if quest not in SUBMITTED state."""
    assert QuestStateMachine.can_user_dispute(open_quest, "creator1") is False


# Test helper methods
def test_is_requestor(submitted_quest):
    """Test _is_requestor helper method."""
    assert QuestStateMachine._is_requestor(submitted_quest, "creator1") is True
    assert QuestStateMachine._is_requestor(submitted_quest, "performer1") is False
    assert QuestStateMachine._is_requestor(submitted_quest, "other_user") is False


def test_is_performer(submitted_quest):
    """Test _is_performer helper method."""
    assert QuestStateMachine._is_performer(submitted_quest, "creator1") is False
    assert QuestStateMachine._is_performer(submitted_quest, "performer1") is True
    assert QuestStateMachine._is_performer(submitted_quest, "other_user") is False


def test_has_dual_attestation_false(submitted_quest):
    """Test _has_dual_attestation returns False with insufficient attestations."""
    # No attestations
    assert QuestStateMachine._has_dual_attestation(submitted_quest) is False
    
    # One attestation
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    assert QuestStateMachine._has_dual_attestation(submitted_quest) is False


def test_has_dual_attestation_true(submitted_quest):
    """Test _has_dual_attestation returns True with dual attestation."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    submitted_quest.attestations.append(
        Attestation(user_id="performer1", role="performer", attested_at=datetime.utcnow())
    )
    assert QuestStateMachine._has_dual_attestation(submitted_quest) is True


# Test all can_user_ methods
def test_can_user_claim_edge_cases(open_quest):
    """Test edge cases for can_user_claim."""
    # Quest without performerId should allow claiming
    assert QuestStateMachine.can_user_claim(open_quest, "new_user") is True
    
    # Quest with wrong status
    open_quest.status = QuestStatus.CLAIMED
    assert QuestStateMachine.can_user_claim(open_quest, "new_user") is False


def test_can_user_submit_edge_cases(claimed_quest):
    """Test edge cases for can_user_submit."""
    # Quest with wrong status
    claimed_quest.status = QuestStatus.OPEN
    assert QuestStateMachine.can_user_submit(claimed_quest, "performer1") is False
    
    # Quest without performerId
    claimed_quest.status = QuestStatus.CLAIMED
    claimed_quest.performerId = None
    assert QuestStateMachine.can_user_submit(claimed_quest, "performer1") is False


# Additional tests for expire transition (missing coverage)
def test_validate_transition_expire_from_open_success(open_quest):
    """Test that an OPEN quest can expire."""
    is_valid, err = QuestStateMachine.validate_transition(
        open_quest, "system_user", QuestStatus.OPEN, QuestStatus.EXPIRED
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_expire_from_claimed_success(claimed_quest):
    """Test that a CLAIMED quest can expire."""
    is_valid, err = QuestStateMachine.validate_transition(
        claimed_quest, "system_user", QuestStatus.CLAIMED, QuestStatus.EXPIRED
    )
    assert is_valid is True
    assert err is None


def test_validate_transition_expire_from_submitted_is_invalid(submitted_quest):
    """Test that a SUBMITTED quest cannot expire via the state machine."""
    is_valid, err = QuestStateMachine.validate_transition(
        submitted_quest, "system_user", QuestStatus.SUBMITTED, QuestStatus.EXPIRED
    )
    assert is_valid is False
    assert "Invalid transition" in err


# Tests for untested public methods
def test_can_transition():
    """Test the can_transition helper for allowed and disallowed paths."""
    # Allowed
    assert QuestStateMachine.can_transition(QuestStatus.OPEN, QuestStatus.CLAIMED) is True
    assert QuestStateMachine.can_transition(QuestStatus.SUBMITTED, QuestStatus.COMPLETE) is True
    
    # Disallowed
    assert QuestStateMachine.can_transition(QuestStatus.OPEN, QuestStatus.SUBMITTED) is False
    assert QuestStateMachine.can_transition(QuestStatus.COMPLETE, QuestStatus.OPEN) is False


def test_get_user_role(submitted_quest):
    """Test get_user_role for all participant types and a non-participant."""
    assert QuestStateMachine.get_user_role(submitted_quest, "creator1") == "requestor"
    assert QuestStateMachine.get_user_role(submitted_quest, "performer1") == "performer"
    assert QuestStateMachine.get_user_role(submitted_quest, "other_user") is None


# Edge cases and security boundaries
def test_has_dual_attestation_with_duplicate_roles(submitted_quest):
    """Test that two attestations from the same role do not grant dual attestation."""
    submitted_quest.attestations.append(
        Attestation(user_id="creator1", role="requestor", attested_at=datetime.utcnow())
    )
    submitted_quest.attestations.append(
        Attestation(user_id="another_creator_friend", role="requestor", attested_at=datetime.utcnow())
    )
    # The use of a set should correctly handle this, but the test confirms it.
    assert QuestStateMachine._has_dual_attestation(submitted_quest) is False
    assert QuestStateMachine.is_ready_for_completion(submitted_quest) is False


def test_can_user_attest_non_participant(submitted_quest):
    """Security: Test that a random user cannot attest."""
    assert QuestStateMachine.can_user_attest(submitted_quest, "random_hacker") is False


def test_can_user_claim_creator_cannot_claim(open_quest):
    """Test the can_user_claim convenience method denies the creator."""
    assert QuestStateMachine.can_user_claim(open_quest, "creator1") is False


def test_validate_transition_unclaim_quest_with_no_performer(claimed_quest):
    """Edge Case: Test unclaiming a quest that is CLAIMED but has no performerId."""
    claimed_quest.performerId = None
    is_valid, err = QuestStateMachine.validate_transition(
        claimed_quest, "performer1", QuestStatus.CLAIMED, QuestStatus.OPEN
    )
    assert is_valid is False
    assert "Only performer can unclaim" in err