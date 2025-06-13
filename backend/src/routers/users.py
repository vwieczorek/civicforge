"""
User-related operations router
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict
import logging
from eth_utils import is_checksum_address

from ..auth import get_current_user_id
from ..db import db_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


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


@router.put("/users/wallet", response_model=Dict[str, str])
async def update_wallet_address(
    wallet_address: str = Body(...),
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