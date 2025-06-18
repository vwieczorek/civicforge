"""
Quest action operations router (claim, submit, dispute)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import logging

from ..models import Quest, QuestStatus, QuestSubmission, QuestDispute
from ..state_machine import QuestStateMachine
from ..auth import get_current_user_id
from ..db import get_db_client, DynamoDBClient
from ..sanitizer import sanitize_submission_text, sanitize_dispute_reason
from ..rate_limiter import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quests"])


@router.post("/quests/{quest_id}/claim", response_model=Quest)
@limiter.limit(RATE_LIMITS["claim_quest"])
async def claim_quest(
    request: Request,
    quest_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> Quest:
    """Claim an open quest"""
    # First, check if quest exists and get its current state
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Use state machine for authorization checks
    if not QuestStateMachine.can_user_claim(quest, user_id):
        if quest.creatorId == user_id:
            raise HTTPException(status_code=400, detail="Cannot claim your own quest")
        elif quest.status != QuestStatus.OPEN:
            raise HTTPException(status_code=400, detail=f"Quest is not available for claiming. Status: {quest.status}")
        elif quest.performerId is not None:
            raise HTTPException(status_code=409, detail="Quest already claimed")
        else:
            raise HTTPException(status_code=400, detail="Cannot claim this quest")
    
    # Attempt atomic claim
    success = await db.claim_quest_atomic(quest_id, user_id)
    
    if not success:
        # Fetch the latest state to provide accurate error message
        updated_quest = await db.get_quest(quest_id)
        if updated_quest and updated_quest.status != QuestStatus.OPEN:
            raise HTTPException(
                status_code=409, 
                detail=f"Quest is no longer available. Current status: {updated_quest.status}"
            )
        else:
            raise HTTPException(
                status_code=409,
                detail="Quest was just claimed by another user. Please try a different quest."
            )
    
    # Return the updated quest
    updated_quest = await db.get_quest(quest_id)
    return updated_quest


@router.post("/quests/{quest_id}/submit", response_model=Quest)
@limiter.limit(RATE_LIMITS["submit_quest"])
async def submit_quest(
    request: Request,
    quest_id: str,
    submission: QuestSubmission,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> Quest:
    """Submit completed work for attestation"""
    # Check if quest exists
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Use state machine for authorization checks
    if not QuestStateMachine.can_user_submit(quest, user_id):
        if quest.status != QuestStatus.CLAIMED:
            raise HTTPException(
                status_code=400,
                detail=f"Quest must be in CLAIMED status to submit. Current status: {quest.status}"
            )
        else:
            raise HTTPException(
                status_code=403,
                detail="Only the assigned performer can submit work"
            )
    
    # Sanitize submission text to prevent XSS
    sanitized_text = sanitize_submission_text(submission.submissionText)
    
    # Attempt atomic submission
    success = await db.submit_quest_atomic(
        quest_id, 
        user_id, 
        sanitized_text
    )
    
    if not success:
        # Get latest state for accurate error message
        updated_quest = await db.get_quest(quest_id)
        if updated_quest and updated_quest.status != QuestStatus.CLAIMED:
            raise HTTPException(
                status_code=400,
                detail=f"Quest is in {updated_quest.status} status. Can only submit when CLAIMED."
            )
        else:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to submit this quest"
            )
    
    # Return updated quest
    updated_quest = await db.get_quest(quest_id)
    return updated_quest


@router.post("/quests/{quest_id}/dispute", response_model=Quest)
@limiter.limit(RATE_LIMITS["dispute_quest"])
async def dispute_quest(
    request: Request,
    quest_id: str,
    dispute: QuestDispute,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> Quest:
    """Initiate dispute resolution for a quest"""
    # Sanitize dispute reason to prevent XSS
    sanitized_reason = sanitize_dispute_reason(dispute.reason)
    
    # Use atomic operation to prevent race conditions
    success = await db.dispute_quest_atomic(quest_id, user_id, sanitized_reason)
    
    if not success:
        raise HTTPException(
            status_code=409, 
            detail="Quest could not be disputed. It may no longer be in a submittable state or you are not authorized."
        )
    
    # In production, this would trigger notification to arbiters
    logger.info(f"Dispute initiated for quest {quest_id} by user {user_id}: {sanitized_reason}")
    
    # Return the updated quest
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    return quest