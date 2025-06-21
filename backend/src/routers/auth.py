"""
Authentication endpoints for logout and session management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Optional
import logging

from ..auth import get_current_user_claims, get_current_user_id
from ..utils.token_blacklist import revoke_token, generate_jti

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


class LogoutRequest(BaseModel):
    """Request body for logout"""
    revoke_all_sessions: bool = False
    reason: Optional[str] = "user_logout"


class LogoutResponse(BaseModel):
    """Response for logout"""
    success: bool
    message: str


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: LogoutRequest,
    claims: Dict = Depends(get_current_user_claims),
    user_id: str = Depends(get_current_user_id)
) -> LogoutResponse:
    """
    Logout user and revoke their tokens
    
    This endpoint revokes the current token and optionally all user sessions.
    Note: Cognito doesn't include JTI by default, so this requires custom token generation.
    """
    try:
        # Get token details from claims
        jti = claims.get("jti")
        exp = claims.get("exp", 0)
        
        if not jti:
            # If no JTI, we can't revoke individual tokens
            # Log this as a warning - in production, all tokens should have JTI
            logger.warning(f"Token without JTI used for logout by user {user_id}")
            return LogoutResponse(
                success=False,
                message="Token revocation not supported for this token type. Please clear your local session."
            )
        
        # Revoke the current token
        success = revoke_token(
            token_jti=jti,
            user_id=user_id,
            exp_timestamp=exp,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke token"
            )
        
        # TODO: If revoke_all_sessions is True, implement bulk revocation
        # This would require maintaining a sessions table or using Cognito admin APIs
        if request.revoke_all_sessions:
            logger.info(f"Bulk session revocation requested for user {user_id}")
            # In production, this would:
            # 1. Query all active sessions for the user
            # 2. Revoke all associated tokens
            # 3. Clear any refresh tokens via Cognito Admin API
        
        return LogoutResponse(
            success=True,
            message="Successfully logged out"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout"
        )


@router.post("/revoke-sessions", response_model=LogoutResponse)
async def revoke_all_sessions(
    user_id: str = Depends(get_current_user_id)
) -> LogoutResponse:
    """
    Revoke all sessions for the current user
    
    This is useful when a user suspects their account has been compromised.
    """
    try:
        # TODO: Implement bulk session revocation
        # This would require:
        # 1. Maintaining a sessions table with all active JTIs
        # 2. Adding all JTIs to the blacklist
        # 3. Using Cognito Admin API to revoke refresh tokens
        
        logger.info(f"All sessions revocation requested for user {user_id}")
        
        # For now, return a message indicating the feature is pending
        return LogoutResponse(
            success=False,
            message="Bulk session revocation is not yet implemented. Please change your password to invalidate all sessions."
        )
        
    except Exception as e:
        logger.error(f"Session revocation error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during session revocation"
        )