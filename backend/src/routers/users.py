"""
User-related operations router
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request
import json
import base64
import binascii
from typing import Dict, Optional
import logging
from eth_utils import is_checksum_address

from ..auth import get_current_user_id
from ..db import get_db_client, DynamoDBClient
from ..rate_limiter import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


@router.get("/users/{user_id}", response_model=Dict)
async def get_user_profile(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client),
    limit: int = Query(20, gt=0, le=100, description="Number of quests to return"),
    created_quests_token: Optional[str] = Query(None, description="Pagination token for created quests"),
    performed_quests_token: Optional[str] = Query(None, description="Pagination token for performed quests")
) -> Dict:
    """Get user profile with quest statistics using token-based pagination"""
    # Allow users to view their own profile or others (for public profiles)
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Decode pagination tokens if provided
    created_start_key = None
    performed_start_key = None
    
    if created_quests_token:
        try:
            created_start_key = json.loads(base64.b64decode(created_quests_token))
        except (json.JSONDecodeError, binascii.Error, TypeError):
            raise HTTPException(status_code=400, detail="Invalid created quests pagination token")
    
    if performed_quests_token:
        try:
            performed_start_key = json.loads(base64.b64decode(performed_quests_token))
        except (json.JSONDecodeError, binascii.Error, TypeError):
            raise HTTPException(status_code=400, detail="Invalid performed quests pagination token")
    
    # Get user's created quests with pagination
    created_quests, created_next_key = await db.get_user_created_quests(user_id, limit=limit, start_key=created_start_key)
    
    # Get user's performed quests with pagination
    performed_quests, performed_next_key = await db.get_user_performed_quests(user_id, limit=limit, start_key=performed_start_key)
    
    # Prepare response
    profile_data = user.dict()
    profile_data["createdQuests"] = created_quests
    profile_data["performedQuests"] = performed_quests
    
    # Add pagination tokens if there are more results
    if created_next_key:
        profile_data["createdQuestsNextToken"] = base64.b64encode(json.dumps(created_next_key).encode()).decode()
    
    if performed_next_key:
        profile_data["performedQuestsNextToken"] = base64.b64encode(json.dumps(performed_next_key).encode()).decode()
    
    # Remove sensitive data if viewing another user's profile
    if user_id != current_user_id:
        profile_data.pop("walletAddress", None)
        profile_data.pop("questCreationPoints", None)
    
    return profile_data


@router.put("/users/wallet", response_model=Dict[str, str])
@limiter.limit(RATE_LIMITS["update_wallet"])
async def update_wallet_address(
    request: Request,
    wallet_address: str = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
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
        await db.update_user_wallet(user_id, wallet_address)
        return {"message": "Wallet address updated successfully", "address": wallet_address}
    except Exception as e:
        logger.error(f"Failed to update wallet address for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while updating the wallet address."
        )