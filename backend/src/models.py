"""
Core data models for CivicForge dual-attestation system
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, List, Literal, Set
from datetime import datetime
from enum import Enum
import bleach


# HTML sanitization configuration
ALLOWED_TAGS = [
    'p', 'br', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
}

def clean_html(text: str) -> str:
    """Centralized function to sanitize user-provided HTML."""
    if not text:
        return text
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True  # Strips disallowed tags instead of escaping them
    ).strip()


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
    walletAddress: Optional[str] = None  # Ethereum wallet address for signatures
    reputation: int = 0
    experience: int = 0
    questCreationPoints: int = 10  # Anti-spam: points for creating quests
    processedRewardIds: Optional[List[str]] = None  # Track processed rewards for idempotency
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
    updatedAt: Optional[datetime] = None
    
    # Submission data
    submissionText: Optional[str] = None
    
    # Dispute data
    dispute_reason: Optional[str] = None
    
    # TTL for auto-expiry
    ttl: Optional[int] = None
    
    # Computed properties for easy access in application code
    @property
    def attester_ids(self) -> List[str]:
        """Get list of user IDs who have attested"""
        return [att.user_id for att in self.attestations]
    
    @property
    def has_requestor_attestation(self) -> bool:
        """Check if requestor has attested"""
        return any(att.role == 'requestor' for att in self.attestations)
    
    @property
    def has_performer_attestation(self) -> bool:
        """Check if performer has attested"""
        return any(att.role == 'performer' for att in self.attestations)


class QuestDB(Quest):
    """Quest model with DynamoDB-specific denormalized fields for performance"""
    
    # Denormalized fields for DynamoDB queries and atomic operations
    hasRequestorAttestation: bool = False
    hasPerformerAttestation: bool = False
    attesterIds: Optional[Set[str]] = None  # DynamoDB String Set for efficient queries
    
    @model_validator(mode='before')
    @classmethod
    def compute_derived_fields(cls, data):
        """Automatically compute denormalized fields from attestations"""
        if isinstance(data, dict):
            attestations = data.get('attestations', [])
            if attestations:
                # Extract attester IDs
                attester_ids = set()
                roles = set()
                
                for att in attestations:
                    if isinstance(att, dict):
                        attester_ids.add(att.get('user_id'))
                        roles.add(att.get('role'))
                    else:
                        # Handle Attestation objects
                        attester_ids.add(att.user_id)
                        roles.add(att.role)
                
                # Set denormalized fields
                data['attesterIds'] = attester_ids if attester_ids else None
                data['hasRequestorAttestation'] = 'requestor' in roles
                data['hasPerformerAttestation'] = 'performer' in roles
            else:
                data['attesterIds'] = None
                data['hasRequestorAttestation'] = False
                data['hasPerformerAttestation'] = False
        
        return data


# API Request/Response Models

class QuestCreate(BaseModel):
    """Request model for creating a new quest"""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=2000)
    rewardXp: int = Field(100, ge=10, le=1000)
    rewardReputation: int = Field(10, ge=1, le=100)
    
    @validator('title', 'description', pre=True, always=True)
    def sanitize_fields(cls, v):
        """Sanitize free-text fields to prevent XSS."""
        return clean_html(v)


class QuestSubmission(BaseModel):
    """Performer's submission of completed work"""
    submissionText: str = Field(..., min_length=10, max_length=2000)
    
    @validator('submissionText', pre=True, always=True)
    def sanitize_fields(cls, v):
        """Sanitize free-text fields to prevent XSS."""
        return clean_html(v)


class AttestationRequest(BaseModel):
    """Request to attest quest completion"""
    notes: Optional[str] = Field(None, max_length=500)
    signature: Optional[str] = Field(None, description="Cryptographic signature for attestation")
    
    @validator('notes', pre=True, always=True)
    def sanitize_notes(cls, v):
        """Sanitize notes field to prevent XSS."""
        if v is None:
            return None
        return clean_html(v)


class QuestDispute(BaseModel):
    """Request model for disputing a quest"""
    reason: str = Field(..., min_length=20, max_length=1000)
    
    @validator('reason', pre=True, always=True)
    def sanitize_reason(cls, v):
        """Sanitize the dispute reason to prevent XSS."""
        return clean_html(v)


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    status_code: int
    timestamp: datetime


class FailedReward(BaseModel):
    """Track failed reward distributions for retry with idempotency"""
    rewardId: str  # Primary key for the failed rewards table
    questId: str
    userId: str
    xpAmount: int = 0
    reputationAmount: int = 0
    questPointsAmount: int = 0
    errorMessage: str
    retryCount: int = 0
    status: Literal["pending", "retrying", "resolved", "abandoned"] = "pending"
    leaseOwner: Optional[str] = None  # Lambda request ID that owns the lease
    leaseExpiresAt: Optional[datetime] = None  # When the lease expires
    createdAt: datetime
    updatedAt: datetime
    lastRetryAt: Optional[datetime] = None
    resolvedAt: Optional[datetime] = None