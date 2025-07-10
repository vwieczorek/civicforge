"""
Consent Manager Interface

Manages user consent for data sharing and processing in CivicForge.
Ensures nothing happens without explicit user consent.
"""

from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


class ConsentType(Enum):
    """Types of consent that can be granted"""
    SHARE_BASIC_PROFILE = "share_basic_profile"
    SHARE_SKILLS = "share_skills"
    SHARE_AVAILABILITY = "share_availability"
    SHARE_LOCATION = "share_location"
    MATCH_OPPORTUNITIES = "match_opportunities"
    CONTACT_BY_ORGANIZERS = "contact_by_organizers"
    ANONYMOUS_ANALYTICS = "anonymous_analytics"


@dataclass
class ConsentRequest:
    """Request for user consent"""
    consent_type: ConsentType
    purpose: str
    data_categories: List[str]
    recipient: Optional[str] = None
    duration: Optional[timedelta] = None
    
    
@dataclass
class ConsentRecord:
    """Record of granted consent"""
    consent_type: ConsentType
    granted_at: datetime
    expires_at: Optional[datetime]
    purpose: str
    conditions: List[str] = field(default_factory=list)
    revoked: bool = False
    revoked_at: Optional[datetime] = None


class ConsentManager(Protocol):
    """
    Protocol for consent management operations.
    
    Future implementations will:
    - Track all consent grants
    - Enforce consent expiration
    - Handle consent revocation
    - Provide consent audit trail
    """
    
    def request_consent(self, request: ConsentRequest) -> bool:
        """Request consent from user"""
        ...
    
    def check_consent(self, consent_type: ConsentType, purpose: str) -> bool:
        """Check if valid consent exists for operation"""
        ...
    
    def revoke_consent(self, consent_type: ConsentType) -> None:
        """Revoke previously granted consent"""
        ...
    
    def get_active_consents(self) -> List[ConsentRecord]:
        """Get all active consent records"""
        ...
    
    def get_consent_history(self) -> List[ConsentRecord]:
        """Get full consent history including revoked"""
        ...


class MockConsentManager:
    """
    Mock implementation for Phase 1 development.
    Tracks consent but auto-grants for development ease.
    """
    
    def __init__(self):
        self._consents: List[ConsentRecord] = []
        self._auto_consent_types = {
            ConsentType.SHARE_SKILLS,
            ConsentType.SHARE_AVAILABILITY,
            ConsentType.MATCH_OPPORTUNITIES
        }
    
    def request_consent(self, request: ConsentRequest) -> bool:
        """Auto-grant certain consents for development"""
        # In future: Show consent UI
        # For now: Auto-grant non-sensitive consents
        
        granted = request.consent_type in self._auto_consent_types
        
        if granted:
            expires_at = None
            if request.duration:
                expires_at = datetime.now() + request.duration
                
            record = ConsentRecord(
                consent_type=request.consent_type,
                granted_at=datetime.now(),
                expires_at=expires_at,
                purpose=request.purpose
            )
            self._consents.append(record)
            
        return granted
    
    def check_consent(self, consent_type: ConsentType, purpose: str) -> bool:
        """Check if valid consent exists"""
        now = datetime.now()
        
        for consent in self._consents:
            if (consent.consent_type == consent_type and
                not consent.revoked and
                (consent.expires_at is None or consent.expires_at > now)):
                return True
                
        return False
    
    def revoke_consent(self, consent_type: ConsentType) -> None:
        """Revoke consent"""
        now = datetime.now()
        
        for consent in self._consents:
            if consent.consent_type == consent_type and not consent.revoked:
                consent.revoked = True
                consent.revoked_at = now
    
    def get_active_consents(self) -> List[ConsentRecord]:
        """Get active consents"""
        now = datetime.now()
        
        return [
            c for c in self._consents
            if not c.revoked and (c.expires_at is None or c.expires_at > now)
        ]
    
    def get_consent_history(self) -> List[ConsentRecord]:
        """Get all consent records"""
        return self._consents.copy()