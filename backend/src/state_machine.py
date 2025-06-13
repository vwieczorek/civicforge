"""
Quest state machine for secure transitions
Enforces business rules for the dual-attestation model
"""

from typing import Dict, Tuple, Optional
from .models import Quest, QuestStatus


class QuestStateMachine:
    """Manages quest state transitions with security checks"""
    
    # Define allowed state transitions
    ALLOWED_TRANSITIONS: Dict[Tuple[QuestStatus, QuestStatus], str] = {
        (QuestStatus.OPEN, QuestStatus.CLAIMED): "claim",
        (QuestStatus.CLAIMED, QuestStatus.OPEN): "unclaim", 
        (QuestStatus.CLAIMED, QuestStatus.SUBMITTED): "submit",
        (QuestStatus.SUBMITTED, QuestStatus.COMPLETE): "complete",
        (QuestStatus.SUBMITTED, QuestStatus.DISPUTED): "dispute",
        (QuestStatus.OPEN, QuestStatus.EXPIRED): "expire",
        (QuestStatus.CLAIMED, QuestStatus.EXPIRED): "expire",
    }
    
    @staticmethod
    def can_transition(from_status: QuestStatus, to_status: QuestStatus) -> bool:
        """Check if a state transition is allowed"""
        return (from_status, to_status) in QuestStateMachine.ALLOWED_TRANSITIONS
    
    @staticmethod
    def validate_transition(
        quest: Quest,
        user_id: str,
        from_status: QuestStatus,
        to_status: QuestStatus
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if user can perform the state transition
        Returns (is_valid, error_message)
        """
        if not QuestStateMachine.can_transition(from_status, to_status):
            return False, f"Invalid transition: {from_status} → {to_status}"
        
        if quest.status != from_status:
            return False, f"Quest is not in expected state: {from_status}"
        
        transition_type = QuestStateMachine.ALLOWED_TRANSITIONS[(from_status, to_status)]
        
        # Validate based on transition type
        if transition_type == "claim":
            if user_id == quest.creatorId:
                return False, "cannot claim their own quest"
            if quest.performerId is not None:
                return False, "Quest already claimed"
                
        elif transition_type == "unclaim":
            if user_id != quest.performerId:
                return False, "Only performer can unclaim"
                
        elif transition_type == "submit":
            if user_id != quest.performerId:
                return False, "Only performer can submit"
                
        elif transition_type == "complete":
            # Must have dual attestation
            if not QuestStateMachine._has_dual_attestation(quest):
                return False, "Requires attestation from both parties"
                
        elif transition_type == "dispute":
            if user_id not in [quest.creatorId, quest.performerId]:
                return False, "Only involved parties can dispute"
        
        return True, None
    
    @staticmethod
    def _has_dual_attestation(quest: Quest) -> bool:
        """Check if both requestor and performer have attested"""
        if not quest.attestations or len(quest.attestations) < 2:
            return False
        
        roles = {a.role for a in quest.attestations}
        return "requestor" in roles and "performer" in roles
    
    @staticmethod
    def _is_requestor(quest: Quest, user_id: str) -> bool:
        """Check if user is the quest requestor (creator)"""
        return quest.creatorId == user_id
    
    @staticmethod
    def _is_performer(quest: Quest, user_id: str) -> bool:
        """Check if user is the quest performer"""
        return quest.performerId == user_id
    
    @staticmethod
    def can_user_attest(quest: Quest, user_id: str) -> bool:
        """
        Check if user can attest to this quest.
        Enforces state, role, and idempotency requirements.
        """
        # 1. State Check: Must be in SUBMITTED state to accept attestations
        if quest.status != QuestStatus.SUBMITTED:
            return False
        
        # 2. Role Check: User must be a participant (requestor or performer)
        is_participant = (
            QuestStateMachine._is_requestor(quest, user_id) or 
            QuestStateMachine._is_performer(quest, user_id)
        )
        if not is_participant:
            return False
        
        # 3. Idempotency Check: User must not have already attested
        if any(att.user_id == user_id for att in quest.attestations):
            return False
        
        return True
    
    @staticmethod
    def is_ready_for_completion(quest: Quest) -> bool:
        """
        Check if quest is ready for completion.
        Requires dual attestation from both parties.
        """
        return (
            quest.status == QuestStatus.SUBMITTED and
            QuestStateMachine._has_dual_attestation(quest)
        )
    
    @staticmethod
    def can_user_claim(quest: Quest, user_id: str) -> bool:
        """Check if user can claim this quest"""
        if quest.status != QuestStatus.OPEN:
            return False
        
        if QuestStateMachine._is_requestor(quest, user_id):
            return False  # Cannot claim own quest
        
        if quest.performerId is not None:
            return False  # Already claimed
        
        return True
    
    @staticmethod
    def can_user_submit(quest: Quest, user_id: str) -> bool:
        """Check if user can submit work for this quest"""
        if quest.status != QuestStatus.CLAIMED:
            return False
        
        return QuestStateMachine._is_performer(quest, user_id)
    
    @staticmethod
    def can_user_dispute(quest: Quest, user_id: str) -> bool:
        """Check if user can dispute this quest"""
        if quest.status != QuestStatus.SUBMITTED:
            return False
        
        return (
            QuestStateMachine._is_requestor(quest, user_id) or
            QuestStateMachine._is_performer(quest, user_id)
        )
    
    @staticmethod
    def get_user_role(quest: Quest, user_id: str) -> Optional[str]:
        """Get user's role in this quest"""
        if user_id is None:
            return None
        if QuestStateMachine._is_requestor(quest, user_id):
            return "requestor"
        elif QuestStateMachine._is_performer(quest, user_id):
            return "performer"
        else:
            return None