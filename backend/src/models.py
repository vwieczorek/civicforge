"""
Core data models for CivicForge dual-attestation system
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class QuestStatus(str, Enum):
    """Quest lifecycle states"""
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    SUBMITTED = "SUBMITTED"
    COMPLETE = "COMPLETE"
    DISPUTED = "DISPUTED"
    EXPIRED = "EXPIRED"


class Attestation(BaseModel):
    """Proof of quest completion from either party"""
    user_id: str
    role: Literal["requestor", "performer"]
    attested_at: datetime
    signature: Optional[str] = None  # Future: cryptographic proof


class User(BaseModel):
    """User profile data"""
    userId: str  # Cognito sub
    username: str
    reputation: int = 0
    experience: int = 0
    createdAt: datetime
    updatedAt: datetime


class Quest(BaseModel):
    """Core quest model with dual-attestation support"""
    questId: str
    title: str
    description: str
    status: QuestStatus = QuestStatus.OPEN
    
    # Parties involved
    creatorId: str  # The requestor
    performerId: Optional[str] = None  # The performer who claims it
    
    # Rewards
    rewardXp: int = Field(100, ge=10, le=1000)
    rewardReputation: int = Field(10, ge=1, le=100)
    
    # Attestation tracking
    attestations: List[Attestation] = []
    
    # Timestamps
    createdAt: datetime
    claimedAt: Optional[datetime] = None
    submittedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    
    # Submission data
    submissionText: Optional[str] = None
    
    # TTL for auto-expiry
    ttl: Optional[int] = None


# API Request/Response Models

class QuestSubmission(BaseModel):
    """Performer's submission of completed work"""
    submissionText: str = Field(..., min_length=10, max_length=2000)


class AttestationRequest(BaseModel):
    """Request to attest quest completion"""
    notes: Optional[str] = Field(None, max_length=500)


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    status_code: int
    timestamp: datetime