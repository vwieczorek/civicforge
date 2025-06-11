"""
Quest state machine for secure transitions
Enforces business rules for the dual-attestation model
"""

from typing import Dict, Tuple, Optional
from datetime import datetime
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
                return False, "Cannot claim your own quest"
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