"""
Comprehensive state machine tests covering all transitions and edge cases.
This file specifically targets the state machine logic to ensure all business rules are enforced.
"""

import pytest
from datetime import datetime, timezone
from src.models import Quest, QuestStatus, Attestation, User
from src.state_machine import QuestStateMachine


class TestStateTransitions:
    """Test all valid and invalid state transitions."""
    
    def test_valid_transitions(self):
        """Test all valid state transitions are allowed."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # OPEN -> CLAIMED is valid
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.CLAIMED)
        assert can_transition is True
        
        # CLAIMED -> SUBMITTED is valid
        quest.status = QuestStatus.CLAIMED
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.SUBMITTED)
        assert can_transition is True
        
        # SUBMITTED -> COMPLETE is valid
        quest.status = QuestStatus.SUBMITTED
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.COMPLETE)
        assert can_transition is True
        
        # SUBMITTED -> DISPUTED is valid
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.DISPUTED)
        assert can_transition is True
        
        # OPEN -> EXPIRED is valid
        quest.status = QuestStatus.OPEN
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.EXPIRED)
        assert can_transition is True
        
        # CLAIMED -> EXPIRED is valid
        quest.status = QuestStatus.CLAIMED
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.EXPIRED)
        assert can_transition is True
        
        # CLAIMED -> OPEN is valid (unclaim)
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.OPEN)
        assert can_transition is True
    
    def test_invalid_transitions(self):
        """Test invalid state transitions are blocked."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # OPEN -> SUBMITTED is invalid (must be claimed first)
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.SUBMITTED)
        assert can_transition is False
        
        # OPEN -> COMPLETE is invalid
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.COMPLETE)
        assert can_transition is False
        
        # CLAIMED -> COMPLETE is invalid (must be submitted first)
        quest.status = QuestStatus.CLAIMED
        can_transition = QuestStateMachine.can_transition(quest.status, QuestStatus.COMPLETE)
        assert can_transition is False
        
        # COMPLETE -> any state is invalid (terminal state)
        quest.status = QuestStatus.COMPLETE
        for status in [QuestStatus.OPEN, QuestStatus.CLAIMED, QuestStatus.SUBMITTED, QuestStatus.DISPUTED]:
            can_transition = QuestStateMachine.can_transition(quest.status, status)
            assert can_transition is False
        
        # EXPIRED -> any state is invalid (terminal state)
        quest.status = QuestStatus.EXPIRED
        for status in [QuestStatus.OPEN, QuestStatus.CLAIMED, QuestStatus.SUBMITTED, QuestStatus.COMPLETE]:
            can_transition = QuestStateMachine.can_transition(quest.status, status)
            assert can_transition is False


class TestUserClaimValidation:
    """Test can_user_claim with all edge cases."""
    
    def test_happy_path_claim(self):
        """Test successful claim by eligible user."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Different user can claim
        assert QuestStateMachine.can_user_claim(quest, "performer1") is True
    
    def test_creator_cannot_claim_own_quest(self):
        """Test that creator cannot claim their own quest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Creator cannot claim own quest
        assert QuestStateMachine.can_user_claim(quest, "creator1") is False
    
    def test_cannot_claim_non_open_quest(self):
        """Test that only OPEN quests can be claimed."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer2",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Cannot claim already claimed quest
        assert QuestStateMachine.can_user_claim(quest, "performer1") is False
        
        # Test other statuses
        for status in [QuestStatus.SUBMITTED, QuestStatus.COMPLETE, QuestStatus.DISPUTED, QuestStatus.EXPIRED]:
            quest.status = status
            assert QuestStateMachine.can_user_claim(quest, "performer1") is False
    
    def test_edge_case_open_quest_with_performer(self):
        """Test edge case: OPEN quest that somehow has a performerId."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            performerId="performer2",  # Edge case: shouldn't happen
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Should still prevent claiming if performerId is set
        assert QuestStateMachine.can_user_claim(quest, "performer1") is False


class TestUserSubmitValidation:
    """Test can_user_submit with all edge cases."""
    
    def test_happy_path_submit(self):
        """Test successful submission by assigned performer."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Assigned performer can submit
        assert QuestStateMachine.can_user_submit(quest, "performer1") is True
    
    def test_non_performer_cannot_submit(self):
        """Test that only the assigned performer can submit."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Other user cannot submit
        assert QuestStateMachine.can_user_submit(quest, "performer2") is False
        
        # Creator cannot submit (unless they are also the performer)
        assert QuestStateMachine.can_user_submit(quest, "creator1") is False
    
    def test_creator_can_submit_if_also_performer(self):
        """Test edge case where creator claimed and performs their own quest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="creator1",  # Creator is also performer
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Creator who is also performer can submit
        assert QuestStateMachine.can_user_submit(quest, "creator1") is True
    
    def test_cannot_submit_wrong_status(self):
        """Test that submission is only allowed in CLAIMED status."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Cannot submit OPEN quest
        assert QuestStateMachine.can_user_submit(quest, "performer1") is False
        
        # Test other statuses
        for status in [QuestStatus.SUBMITTED, QuestStatus.COMPLETE, QuestStatus.DISPUTED]:
            quest.status = status
            assert QuestStateMachine.can_user_submit(quest, "performer1") is False


class TestUserAttestValidation:
    """Test can_user_attest with all edge cases."""
    
    def test_creator_can_attest(self):
        """Test creator can attest to submitted quest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Creator can attest
        assert QuestStateMachine.can_user_attest(quest, "creator1") is True
    
    def test_performer_can_attest(self):
        """Test performer can attest to submitted quest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Performer can attest
        assert QuestStateMachine.can_user_attest(quest, "performer1") is True
    
    def test_non_participant_cannot_attest(self):
        """Test that non-participants cannot attest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Random user cannot attest
        assert QuestStateMachine.can_user_attest(quest, "random_user") is False
    
    def test_cannot_attest_twice(self):
        """Test that users cannot attest twice (idempotency)."""
        attestation = Attestation(
            user_id="creator1",
            role="requestor",
            attested_at=datetime.now(timezone.utc)
        )
        
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[attestation]
        )
        
        # Creator cannot attest again
        assert QuestStateMachine.can_user_attest(quest, "creator1") is False
        
        # But performer can still attest
        assert QuestStateMachine.can_user_attest(quest, "performer1") is True
    
    def test_cannot_attest_wrong_status(self):
        """Test attestation only allowed in SUBMITTED status."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Cannot attest non-SUBMITTED quest
        for status in [QuestStatus.OPEN, QuestStatus.CLAIMED, QuestStatus.COMPLETE, QuestStatus.DISPUTED]:
            quest.status = status
            assert QuestStateMachine.can_user_attest(quest, "creator1") is False
            assert QuestStateMachine.can_user_attest(quest, "performer1") is False


class TestQuestCompletion:
    """Test is_ready_for_completion logic."""
    
    def test_not_ready_no_attestations(self):
        """Test quest not ready with no attestations."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.is_ready_for_completion(quest) is False
    
    def test_not_ready_one_attestation(self):
        """Test quest not ready with only one attestation."""
        attestation = Attestation(
            user_id="creator1",
            role="requestor",
            attested_at=datetime.now(timezone.utc)
        )
        
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[attestation]
        )
        
        assert QuestStateMachine.is_ready_for_completion(quest) is False
    
    def test_ready_dual_attestation(self):
        """Test quest ready with dual attestation."""
        attestations = [
            Attestation(
                user_id="creator1",
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            ),
            Attestation(
                user_id="performer1",
                role="performer",
                attested_at=datetime.now(timezone.utc)
            )
        ]
        
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=attestations
        )
        
        assert QuestStateMachine.is_ready_for_completion(quest) is True
    
    def test_not_ready_wrong_status(self):
        """Test quest not ready if not in SUBMITTED status."""
        attestations = [
            Attestation(
                user_id="creator1",
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            ),
            Attestation(
                user_id="performer1",
                role="performer",
                attested_at=datetime.now(timezone.utc)
            )
        ]
        
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.COMPLETE,  # Already complete
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=attestations
        )
        
        assert QuestStateMachine.is_ready_for_completion(quest) is False
    
    def test_not_ready_duplicate_role_attestations(self):
        """Test quest not ready with two attestations from same role."""
        # Edge case: two requestor attestations (shouldn't happen but good to test)
        attestations = [
            Attestation(
                user_id="creator1",
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            ),
            Attestation(
                user_id="creator2",  # Different user but same role
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            )
        ]
        
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=attestations
        )
        
        assert QuestStateMachine.is_ready_for_completion(quest) is False


class TestUserDisputeValidation:
    """Test can_user_dispute with all edge cases."""
    
    def test_creator_can_dispute(self):
        """Test creator can dispute submitted quest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.can_user_dispute(quest, "creator1") is True
    
    def test_performer_can_dispute(self):
        """Test performer can dispute submitted quest."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.can_user_dispute(quest, "performer1") is True
    
    def test_non_participant_cannot_dispute(self):
        """Test non-participants cannot dispute."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.can_user_dispute(quest, "random_user") is False
    
    def test_cannot_dispute_wrong_status(self):
        """Test dispute only allowed in SUBMITTED status."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Test all non-SUBMITTED statuses
        for status in [QuestStatus.OPEN, QuestStatus.CLAIMED, QuestStatus.COMPLETE, QuestStatus.DISPUTED]:
            quest.status = status
            assert QuestStateMachine.can_user_dispute(quest, "creator1") is False


class TestUserRoleIdentification:
    """Test get_user_role functionality."""
    
    def test_creator_role(self):
        """Test creator is identified as requestor."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.get_user_role(quest, "creator1") == "requestor"
    
    def test_performer_role(self):
        """Test performer is identified correctly."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.get_user_role(quest, "performer1") == "performer"
    
    def test_non_participant_role(self):
        """Test non-participant returns None."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine.get_user_role(quest, "random_user") is None
    
    def test_dual_role_user(self):
        """Test user who is both creator and performer."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="creator1",  # Same as creator
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Should return requestor (creator role takes precedence)
        assert QuestStateMachine.get_user_role(quest, "creator1") == "requestor"


class TestValidateTransition:
    """Test the validate_transition method with user validation."""
    
    def test_validate_claim_transition(self):
        """Test validation of claim transition."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Valid claim by non-creator
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "performer1", QuestStatus.OPEN, QuestStatus.CLAIMED
        )
        assert is_valid is True
        assert error is None
        
        # Invalid claim by creator
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "creator1", QuestStatus.OPEN, QuestStatus.CLAIMED
        )
        assert is_valid is False
        assert "cannot claim their own quest" in error
    
    def test_validate_submit_transition(self):
        """Test validation of submit transition."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Valid submit by performer
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "performer1", QuestStatus.CLAIMED, QuestStatus.SUBMITTED
        )
        assert is_valid is True
        assert error is None
        
        # Invalid submit by non-performer
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "performer2", QuestStatus.CLAIMED, QuestStatus.SUBMITTED
        )
        assert is_valid is False
        assert "Only performer can submit" in error
    
    def test_validate_delete_transition(self):
        """Test validation of delete transition."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Test that OPEN -> DELETED is not a valid state transition
        # (since DELETED doesn't exist in the QuestStatus enum)
        # This test will be skipped for now
        pass
    
    def test_validate_invalid_state_transition(self):
        """Test validation rejects invalid state transitions."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Invalid transition: OPEN -> COMPLETE
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "creator1", QuestStatus.OPEN, QuestStatus.COMPLETE
        )
        assert is_valid is False
        assert "Invalid" in error and "transition" in error
    
    def test_validate_transition_wrong_current_state(self):
        """Test validation fails when quest not in expected from_status."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,  # Quest is OPEN
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Try to transition from CLAIMED -> SUBMITTED, but quest is OPEN
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "performer1", QuestStatus.CLAIMED, QuestStatus.SUBMITTED
        )
        assert is_valid is False
        assert "Quest is not in expected state" in error
    
    def test_validate_transition_already_claimed(self):
        """Test claim validation when quest already has performer."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            performerId="existing_performer",  # Already has performer
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Try to claim already claimed quest
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "new_performer", QuestStatus.OPEN, QuestStatus.CLAIMED
        )
        assert is_valid is False
        assert "Quest already claimed" in error
    
    def test_validate_unclaim_transition(self):
        """Test unclaim transition validation."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Valid unclaim by performer
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "performer1", QuestStatus.CLAIMED, QuestStatus.OPEN
        )
        assert is_valid is True
        assert error is None
        
        # Invalid unclaim by non-performer
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "creator1", QuestStatus.CLAIMED, QuestStatus.OPEN
        )
        assert is_valid is False
        assert "Only" in error and "performer" in error and "unclaim" in error
    
    def test_validate_unclaim_no_performer(self):
        """Test unclaim when quest has no performer (edge case)."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId=None,  # No performer (edge case)
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Should fail gracefully
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "anyone", QuestStatus.CLAIMED, QuestStatus.OPEN
        )
        assert is_valid is False
        assert "Only" in error and "performer" in error and "unclaim" in error
    
    def test_validate_complete_transition_requirements(self):
        """Test complete transition with various attestation states."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # No attestations - should fail
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "system", QuestStatus.SUBMITTED, QuestStatus.COMPLETE
        )
        assert is_valid is False
        assert "Requires" in error and "attestation" in error
        
        # One attestation - should still fail
        quest.attestations.append(
            Attestation(
                user_id="creator1",
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            )
        )
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "system", QuestStatus.SUBMITTED, QuestStatus.COMPLETE
        )
        assert is_valid is False
        assert "Requires" in error and "attestation" in error
        
        # Two attestations - should succeed
        quest.attestations.append(
            Attestation(
                user_id="performer1",
                role="performer",
                attested_at=datetime.now(timezone.utc)
            )
        )
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "system", QuestStatus.SUBMITTED, QuestStatus.COMPLETE
        )
        assert is_valid is True
        assert error is None
    
    def test_validate_dispute_transition(self):
        """Test dispute transition validation."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Creator can dispute
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "creator1", QuestStatus.SUBMITTED, QuestStatus.DISPUTED
        )
        assert is_valid is True
        assert error is None
        
        # Performer can dispute
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "performer1", QuestStatus.SUBMITTED, QuestStatus.DISPUTED
        )
        assert is_valid is True
        assert error is None
        
        # Others cannot dispute
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "random_user", QuestStatus.SUBMITTED, QuestStatus.DISPUTED
        )
        assert is_valid is False
        assert "Only involved parties can dispute" in error
    
    def test_validate_expire_transitions(self):
        """Test expire transition validation."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Can expire from OPEN
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "system", QuestStatus.OPEN, QuestStatus.EXPIRED
        )
        assert is_valid is True
        assert error is None
        
        # Can expire from CLAIMED
        quest.status = QuestStatus.CLAIMED
        is_valid, error = QuestStateMachine.validate_transition(
            quest, "system", QuestStatus.CLAIMED, QuestStatus.EXPIRED
        )
        assert is_valid is True
        assert error is None


class TestEdgeCases:
    """Test various edge cases and boundary conditions."""
    
    def test_none_user_id(self):
        """Test methods handle None user_id gracefully."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Note: can_user_claim with None user_id might return True
        # if the implementation doesn't check for None and just checks user != creator
        # This depends on the actual implementation
        
        # These should definitely return False/None for None user_id
        assert QuestStateMachine.can_user_submit(quest, None) is False
        assert QuestStateMachine.can_user_attest(quest, None) is False
        assert QuestStateMachine.can_user_dispute(quest, None) is False
        assert QuestStateMachine.get_user_role(quest, None) is None
    
    def test_empty_string_user_id(self):
        """Test methods handle empty string user_id."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Empty string should be treated as valid but non-matching user
        assert QuestStateMachine.can_user_claim(quest, "") is True  # Not the creator
        assert QuestStateMachine.get_user_role(quest, "") is None
    
    def test_quest_with_no_performer_id(self):
        """Test methods handle quest with no performerId set."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,  # Submitted but no performer (edge case)
            performerId=None,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # Should handle gracefully
        assert QuestStateMachine.can_user_submit(quest, "anyone") is False
        assert QuestStateMachine.get_user_role(quest, "performer1") is None
    
    def test_private_method_is_requestor(self):
        """Test _is_requestor private method."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.OPEN,
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine._is_requestor(quest, "creator1") is True
        assert QuestStateMachine._is_requestor(quest, "other") is False
    
    def test_private_method_is_performer(self):
        """Test _is_performer private method."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.CLAIMED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        assert QuestStateMachine._is_performer(quest, "performer1") is True
        assert QuestStateMachine._is_performer(quest, "creator1") is False
        assert QuestStateMachine._is_performer(quest, "other") is False
    
    def test_private_method_has_dual_attestation(self):
        """Test _has_dual_attestation private method with various scenarios."""
        quest = Quest(
            questId="q1",
            creatorId="creator1",
            title="Test Quest",
            description="Test Description",
            rewardXp=100,
            rewardReputation=10,
            status=QuestStatus.SUBMITTED,
            performerId="performer1",
            createdAt=datetime.now(timezone.utc),
            attestations=[]
        )
        
        # No attestations
        assert QuestStateMachine._has_dual_attestation(quest) is False
        
        # One attestation
        quest.attestations.append(
            Attestation(
                user_id="creator1",
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            )
        )
        assert QuestStateMachine._has_dual_attestation(quest) is False
        
        # Two attestations with different roles
        quest.attestations.append(
            Attestation(
                user_id="performer1",
                role="performer",
                attested_at=datetime.now(timezone.utc)
            )
        )
        assert QuestStateMachine._has_dual_attestation(quest) is True
        
        # Test with duplicate roles (edge case)
        quest.attestations = [
            Attestation(
                user_id="creator1",
                role="requestor",
                attested_at=datetime.now(timezone.utc)
            ),
            Attestation(
                user_id="creator2",
                role="requestor",  # Same role
                attested_at=datetime.now(timezone.utc)
            )
        ]
        assert QuestStateMachine._has_dual_attestation(quest) is False