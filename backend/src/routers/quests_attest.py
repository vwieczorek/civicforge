"""
Quest attestation operations router
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import logging

from ..models import Quest, QuestStatus, AttestationRequest, Attestation
from ..state_machine import QuestStateMachine
from ..auth import get_current_user_id
from ..db import get_db_client, DynamoDBClient
from ..signature import verify_attestation_signature
from ..feature_flags import feature_flags, FeatureFlag
from ..sanitizer import sanitize_attestation_notes
from ..rate_limiter import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quests"])


@router.post("/quests/{quest_id}/attest", response_model=Quest)
@limiter.limit(RATE_LIMITS["attest_quest"])
async def attest_quest(
    request: Request,
    quest_id: str,
    attestation_request: AttestationRequest,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> Quest:
    """
    Record attestation from requestor or performer.
    Quest completes when both have attested.
    This version uses an atomic update to prevent race conditions.
    """
    # 1. Initial read for validation and role check. This data may be slightly stale.
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Use state machine for authorization checks
    if not QuestStateMachine.can_user_attest(quest, user_id):
        # Determine the specific reason for better error message
        if quest.status != QuestStatus.SUBMITTED:
            raise HTTPException(
                status_code=400, 
                detail=f"Quest must be in SUBMITTED status to attest. Current status: {quest.status}"
            )
        elif any(a.user_id == user_id for a in quest.attestations):
            raise HTTPException(status_code=409, detail="Already attested")
        else:
            raise HTTPException(status_code=403, detail="Not authorized to attest this quest")
    
    # Get user's role using state machine
    role = QuestStateMachine.get_user_role(quest, user_id)
    
    # Verify signature if provided
    if attestation_request.signature:
        # Get user's wallet address
        user = await db.get_user(user_id)
        if not user or not user.walletAddress:
            raise HTTPException(
                status_code=400,
                detail="User must have a registered wallet address to provide signatures"
            )
        
        # Verify the signature
        is_valid = verify_attestation_signature(
            quest_id=quest_id,
            user_id=user_id,
            role=role,
            signature=attestation_request.signature,
            expected_address=user.walletAddress
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Invalid signature. Please ensure you're signing with the correct wallet."
            )
    
    # 2. Prepare and attempt the atomic update.
    new_attestation = Attestation(
        user_id=user_id,
        role=role,
        attested_at=datetime.utcnow(),
        signature=attestation_request.signature
    )
    
    # We must serialize the Pydantic model to a dict for boto3
    attestation_dict = new_attestation.dict()
    attestation_dict['attested_at'] = attestation_dict['attested_at'].isoformat()
    
    success = await db.add_attestation_atomic(quest_id, attestation_dict)
    
    if not success:
        # The conditional update failed. This means the quest's state changed
        # between our read and write. We should return a conflict error.
        raise HTTPException(
            status_code=409,  # 409 Conflict is more appropriate than 400
            detail="Quest state has changed. It may no longer be in SUBMITTED state or was attested simultaneously. Please refresh and try again."
        )

    # 3. Post-update logic: Re-fetch the quest state and handle completion.
    updated_quest = await db.get_quest(quest_id)
    if not updated_quest:
        # This is highly unlikely but a possible edge case.
        raise HTTPException(status_code=500, detail="Quest disappeared after update.")

    # Check for completion using state machine
    if QuestStateMachine.is_ready_for_completion(updated_quest):
        # Complete the quest atomically to prevent double completion
        was_completed = await db.complete_quest_atomic(quest_id)
        
        if was_completed:
            
            # Only award rewards if we successfully completed the quest
            if updated_quest.performerId and feature_flags.is_enabled(
                FeatureFlag.REWARD_DISTRIBUTION, 
                user_id=updated_quest.performerId
            ):
                try:
                    await db.award_rewards(
                        user_id=updated_quest.performerId,
                        xp=updated_quest.rewardXp,
                        reputation=updated_quest.rewardReputation,
                        quest_id=quest_id
                    )
                    # Also award quest creation points to encourage participation
                    await db.award_quest_points(updated_quest.performerId, 2)
                except Exception as e:
                    # Log the error but don't fail the quest completion
                    # The quest is already marked complete, rewards can be retried later
                    logger.warning(f"Quest {quest_id} completed but reward distribution failed: {e}")
                    # Failed rewards are automatically tracked by db.award_rewards()
            elif updated_quest.performerId:
                # Feature flag is off - log for monitoring
                logger.info(f"Quest {quest_id} completed but rewards disabled by feature flag")
            
            # Update our local copy to reflect completion
            updated_quest.status = QuestStatus.COMPLETE
            updated_quest.completedAt = datetime.utcnow()

    return updated_quest