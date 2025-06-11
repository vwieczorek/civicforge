"""
Core API routes for dual-attestation quest system
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging
from botocore.exceptions import ClientError
from eth_utils import is_checksum_address

from .models import (
    Quest, QuestStatus, QuestCreate, QuestSubmission, 
    AttestationRequest, Attestation, ErrorResponse, User, QuestDispute
)
from .state_machine import QuestStateMachine
from .auth import get_current_user_id, require_auth
from .db import db_client, DynamoDBClient
from .signature import verify_attestation_signature, extract_address_from_signature
from .feature_flags import feature_flags, FeatureFlag

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Constants for anti-spam
QUEST_CREATION_COST = 1  # Points required to create a quest


@router.get("/quests", response_model=List[Quest])
async def list_quests(
    status: Optional[QuestStatus] = None,
    _: str = Depends(require_auth)
) -> List[Quest]:
    """List all quests, optionally filtered by status"""
    try:
        quests = await db_client.list_quests(status=status)
        return quests
    except Exception as e:
        logger.error(f"Failed to list quests: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quests")


@router.get("/users/{user_id}", response_model=Dict)
async def get_user_profile(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict:
    """Get user profile with quest statistics"""
    # Allow users to view their own profile or others (for public profiles)
    user = await db_client.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's created quests
    created_quests = await db_client.get_user_created_quests(user_id)
    
    # Get user's performed quests
    performed_quests = await db_client.get_user_performed_quests(user_id)
    
    # Prepare response
    profile_data = user.dict()
    profile_data["createdQuests"] = created_quests
    profile_data["performedQuests"] = performed_quests
    
    # Remove sensitive data if viewing another user's profile
    if user_id != current_user_id:
        profile_data.pop("walletAddress", None)
        profile_data.pop("questCreationPoints", None)
    
    return profile_data


@router.post("/quests", response_model=Quest, status_code=status.HTTP_201_CREATED)
async def create_quest(
    quest: QuestCreate,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Create a new quest"""
    # Check if user has enough points (anti-spam)
    user = await db_client.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.questCreationPoints < QUEST_CREATION_COST:
        raise HTTPException(
            status_code=429, 
            detail=f"Insufficient quest creation points. You have {user.questCreationPoints} but need {QUEST_CREATION_COST}."
        )
    
    # Deduct points atomically
    success = await db_client.deduct_quest_creation_points(user_id)
    if not success:
        raise HTTPException(
            status_code=429,
            detail="Unable to create quest. Please try again later."
        )
    
    quest_data = quest.dict()
    quest_data["questId"] = str(uuid.uuid4())
    quest_data["creatorId"] = user_id
    quest_data["status"] = QuestStatus.OPEN
    quest_data["attestations"] = []
    quest_data["createdAt"] = datetime.utcnow()
    quest_data["updatedAt"] = datetime.utcnow()
    
    # Create Quest object
    new_quest = Quest(**quest_data)
    await db_client.create_quest(new_quest)
    return new_quest


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
    # First, check if quest exists and get its current state
    quest = await db_client.get_quest(quest_id)
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
    success = await db_client.claim_quest_atomic(quest_id, user_id)
    
    if not success:
        # Fetch the latest state to provide accurate error message
        updated_quest = await db_client.get_quest(quest_id)
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
    updated_quest = await db_client.get_quest(quest_id)
    return updated_quest


@router.post("/quests/{quest_id}/submit", response_model=Quest)
async def submit_quest(
    quest_id: str,
    submission: QuestSubmission,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Submit completed work for attestation"""
    # Check if quest exists
    quest = await db_client.get_quest(quest_id)
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
    
    # Attempt atomic submission
    success = await db_client.submit_quest_atomic(
        quest_id, 
        user_id, 
        submission.submissionText
    )
    
    if not success:
        # Get latest state for accurate error message
        updated_quest = await db_client.get_quest(quest_id)
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
    updated_quest = await db_client.get_quest(quest_id)
    return updated_quest


@router.post("/quests/{quest_id}/attest", response_model=Quest)
async def attest_quest(
    quest_id: str,
    attestation_request: AttestationRequest,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """
    Record attestation from requestor or performer.
    Quest completes when both have attested.
    This version uses an atomic update to prevent race conditions.
    """
    # 1. Initial read for validation and role check. This data may be slightly stale.
    quest = await db_client.get_quest(quest_id)
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
        user = await db_client.get_user(user_id)
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
    
    success = await db_client.add_attestation_atomic(quest_id, attestation_dict)
    
    if not success:
        # The conditional update failed. This means the quest's state changed
        # between our read and write. We should return a conflict error.
        raise HTTPException(
            status_code=409,  # 409 Conflict is more appropriate than 400
            detail="Quest state has changed. It may no longer be in SUBMITTED state or was attested simultaneously. Please refresh and try again."
        )

    # 3. Post-update logic: Re-fetch the quest state and handle completion.
    updated_quest = await db_client.get_quest(quest_id)
    if not updated_quest:
        # This is highly unlikely but a possible edge case.
        raise HTTPException(status_code=500, detail="Quest disappeared after update.")

    # Check for completion using state machine
    if QuestStateMachine.is_ready_for_completion(updated_quest):
        # Complete the quest atomically to prevent double completion
        was_completed = await db_client.complete_quest_atomic(quest_id)
        
        if was_completed:
            
            # Only award rewards if we successfully completed the quest
            if updated_quest.performerId and feature_flags.is_enabled(
                FeatureFlag.REWARD_DISTRIBUTION, 
                user_id=updated_quest.performerId
            ):
                try:
                    await db_client.award_rewards(
                        user_id=updated_quest.performerId,
                        xp=updated_quest.rewardXp,
                        reputation=updated_quest.rewardReputation,
                        quest_id=quest_id
                    )
                    # Also award quest creation points to encourage participation
                    await db_client.award_quest_points(updated_quest.performerId, 2)
                except Exception as e:
                    # Log the error but don't fail the quest completion
                    # The quest is already marked complete, rewards can be retried later
                    logger.warning(f"Quest {quest_id} completed but reward distribution failed: {e}")
                    # Failed rewards are automatically tracked by db_client.award_rewards()
            elif updated_quest.performerId:
                # Feature flag is off - log for monitoring
                logger.info(f"Quest {quest_id} completed but rewards disabled by feature flag")
            
            # Update our local copy to reflect completion
            updated_quest.status = QuestStatus.COMPLETE
            updated_quest.completedAt = datetime.utcnow()

    return updated_quest


@router.post("/quests/{quest_id}/dispute", response_model=Quest)
async def dispute_quest(
    quest_id: str,
    request: QuestDispute,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Initiate dispute resolution for a quest"""
    # The reason is already sanitized by the QuestDispute model
    reason = request.reason
    
    # Use atomic operation to prevent race conditions
    success = await db_client.dispute_quest_atomic(quest_id, user_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=409, 
            detail="Quest could not be disputed. It may no longer be in a submittable state or you are not authorized."
        )
    
    # In production, this would trigger notification to arbiters
    logger.info(f"Dispute initiated for quest {quest_id} by user {user_id}: {reason}")
    
    # Return the updated quest
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    return quest


@router.put("/users/wallet", response_model=Dict[str, str])
async def update_wallet_address(
    wallet_address: str,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """Update user's wallet address for signature verification"""
    # Validate Ethereum address format and checksum
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(
            status_code=400,
            detail="Invalid Ethereum wallet address format"
        )
    
    # Verify checksum to prevent typos (EIP-55)
    if not is_checksum_address(wallet_address):
        raise HTTPException(
            status_code=400,
            detail="Invalid Ethereum wallet address checksum. Please verify the address is correct."
        )
    
    # Update user's wallet address
    try:
        await db_client.update_user_wallet(user_id, wallet_address)
        return {"message": "Wallet address updated successfully", "address": wallet_address}
    except Exception as e:
        logger.error(f"Failed to update wallet address: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update wallet address: {str(e)}"
        )


@router.delete("/quests/{quest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quest(
    quest_id: str,
    user_id: str = Depends(get_current_user_id)
) -> None:
    """Delete a quest - only allowed by creator and only if unclaimed"""
    # First check if quest exists
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Check authorization
    if quest.creatorId != user_id:
        raise HTTPException(
            status_code=403, 
            detail="Only the quest creator can delete a quest"
        )
    
    # Check if quest can be deleted (only OPEN quests)
    if quest.status != QuestStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete quest in {quest.status} status. Only OPEN quests can be deleted."
        )
    
    # Attempt atomic delete with conditions
    success = await db_client.delete_quest_atomic(quest_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail="Unable to delete quest. It may have been claimed or modified."
        )
    
    # Refund quest creation points since quest was never completed
    await db_client.award_quest_points(user_id, QUEST_CREATION_COST)
    
    return None


@router.get("/feature-flags", response_model=Dict[str, bool])
async def get_feature_flags(
    _: str = Depends(require_auth)
) -> Dict[str, bool]:
    """Get current feature flag status (admin/debugging endpoint)"""
    return feature_flags.get_all_flags()