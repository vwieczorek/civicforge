"""
Core API routes for dual-attestation quest system
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import Dict

from .models import (
    Quest, QuestStatus, QuestSubmission, 
    AttestationRequest, Attestation, ErrorResponse
)
from .state_machine import QuestStateMachine
from .auth import get_current_user_id, require_auth
from .db import db_client

# Create router
router = APIRouter()


@router.get("/quests/{quest_id}", response_model=Quest)
async def get_quest(
    quest_id: str,
    _: str = Depends(require_auth)
) -> Quest:
    """Get quest details"""
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest


@router.post("/quests/{quest_id}/claim", response_model=Quest)
async def claim_quest(
    quest_id: str,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Claim an open quest"""
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Validate transition
    is_valid, error = QuestStateMachine.validate_transition(
        quest, user_id, QuestStatus.OPEN, QuestStatus.CLAIMED
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Update quest
    quest.status = QuestStatus.CLAIMED
    quest.performerId = user_id
    quest.claimedAt = datetime.utcnow()
    
    await db_client.update_quest(quest)
    return quest


@router.post("/quests/{quest_id}/submit", response_model=Quest)
async def submit_quest(
    quest_id: str,
    submission: QuestSubmission,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Submit completed work for attestation"""
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Validate transition
    is_valid, error = QuestStateMachine.validate_transition(
        quest, user_id, QuestStatus.CLAIMED, QuestStatus.SUBMITTED
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Update quest
    quest.status = QuestStatus.SUBMITTED
    quest.submissionText = submission.submissionText
    quest.submittedAt = datetime.utcnow()
    
    await db_client.update_quest(quest)
    return quest


@router.post("/quests/{quest_id}/attest", response_model=Quest)
async def attest_quest(
    quest_id: str,
    attestation_request: AttestationRequest,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """
    Record attestation from requestor or performer.
    Quest completes when both have attested.
    This is the heart of the dual-attestation model.
    """
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Must be in SUBMITTED state
    if quest.status != QuestStatus.SUBMITTED:
        raise HTTPException(
            status_code=400, 
            detail=f"Quest must be in SUBMITTED state, current: {quest.status}"
        )
    
    # Determine user's role
    if user_id == quest.creatorId:
        role = "requestor"
    elif user_id == quest.performerId:
        role = "performer"
    else:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to attest this quest"
        )
    
    # Check if already attested
    if any(a.user_id == user_id for a in quest.attestations):
        raise HTTPException(status_code=400, detail="Already attested")
    
    # Add attestation
    new_attestation = Attestation(
        user_id=user_id,
        role=role,
        attested_at=datetime.utcnow()
    )
    quest.attestations.append(new_attestation)
    
    # Check if both parties have attested
    has_requestor = any(a.role == "requestor" for a in quest.attestations)
    has_performer = any(a.role == "performer" for a in quest.attestations)
    
    if has_requestor and has_performer:
        # Complete the quest!
        quest.status = QuestStatus.COMPLETE
        quest.completedAt = datetime.utcnow()
        
        # Award XP and reputation to performer
        if quest.performerId:
            await db_client.award_rewards(
                user_id=quest.performerId,
                xp=quest.rewardXp,
                reputation=quest.rewardReputation
            )
    
    await db_client.update_quest(quest)
    return quest


@router.post("/quests/{quest_id}/dispute", response_model=Quest)
async def dispute_quest(
    quest_id: str,
    reason: str,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Initiate dispute resolution for a quest"""
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Validate transition
    is_valid, error = QuestStateMachine.validate_transition(
        quest, user_id, QuestStatus.SUBMITTED, QuestStatus.DISPUTED
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Update quest
    quest.status = QuestStatus.DISPUTED
    quest.dispute_reason = reason
    
    await db_client.update_quest(quest)
    
    # TODO: Notify arbiters
    
    return quest