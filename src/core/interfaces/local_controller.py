"""
Local Controller Interface

Defines the protocol for the Local Controller that runs on user devices,
maintaining control over identity, values, and approval authority.
"""

from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ActionType(Enum):
    """Types of actions that require approval"""
    SHARE_PROFILE = "share_profile"
    CONNECT_USER = "connect_user"
    JOIN_ACTIVITY = "join_activity"
    SHARE_LOCATION = "share_location"
    SHARE_AVAILABILITY = "share_availability"
    SHARE_SKILLS = "share_skills"


@dataclass
class ApprovalRequest:
    """Request for user approval of an action"""
    action_type: ActionType
    description: str
    data_to_share: Dict[str, Any]
    recipient: Optional[str] = None
    purpose: str = ""
    expires_at: Optional[datetime] = None


@dataclass
class ApprovalResponse:
    """User's response to an approval request"""
    approved: bool
    modified_data: Optional[Dict[str, Any]] = None  # User can modify what's shared
    remember_choice: bool = False
    conditions: Optional[List[str]] = None


class LocalController(Protocol):
    """
    Protocol for Local Controller operations.
    
    Future implementations will:
    - Store user identity keys (DIDs)
    - Maintain personal values/constitution
    - Handle approval flows
    - Manage local data storage
    - Support offline operations
    - Provide safety features
    """
    
    def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """Request user approval for an action"""
        ...
    
    def store_value(self, key: str, value: Any) -> None:
        """Store a user value/preference locally"""
        ...
    
    def get_value(self, key: str) -> Optional[Any]:
        """Retrieve a user value/preference"""
        ...
    
    def get_identity(self) -> Dict[str, Any]:
        """Get user's decentralized identity information"""
        ...
    
    def sign_credential(self, credential: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a verifiable credential with user's DID"""
        ...
    
    def queue_offline_action(self, action: Dict[str, Any]) -> None:
        """Queue action for when connectivity returns"""
        ...
    
    def emergency_disconnect(self) -> None:
        """Emergency safety feature - disconnect from all civic activities"""
        ...


class MockLocalController:
    """
    Mock implementation for Phase 1 development.
    Auto-approves with logging for future implementation.
    """
    
    def __init__(self):
        self._values = {}
        self._approval_log = []
        self._offline_queue = []
        self._identity = {
            "did": "did:web:example.com:user:12345",
            "publicKey": "mock_public_key"
        }
    
    def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """Auto-approve for development, but log the request"""
        self._approval_log.append(request)
        
        # In future: Show UI for user approval
        # For now: Auto-approve non-sensitive actions
        auto_approve = request.action_type in [
            ActionType.SHARE_SKILLS,
            ActionType.SHARE_AVAILABILITY
        ]
        
        return ApprovalResponse(
            approved=auto_approve,
            modified_data=None,
            remember_choice=False
        )
    
    def store_value(self, key: str, value: Any) -> None:
        """Store value in memory for now"""
        self._values[key] = value
    
    def get_value(self, key: str) -> Optional[Any]:
        """Retrieve value from memory"""
        return self._values.get(key)
    
    def get_identity(self) -> Dict[str, Any]:
        """Return mock identity for development"""
        return self._identity
    
    def sign_credential(self, credential: Dict[str, Any]) -> Dict[str, Any]:
        """Mock signing - just add a signature field"""
        credential["proof"] = {
            "type": "MockSignature2024",
            "created": datetime.now().isoformat(),
            "verificationMethod": self._identity["did"],
            "proofValue": "mock_signature"
        }
        return credential
    
    def queue_offline_action(self, action: Dict[str, Any]) -> None:
        """Queue action for later sync"""
        self._offline_queue.append({
            "action": action,
            "queued_at": datetime.now(),
            "status": "pending"
        })
    
    def emergency_disconnect(self) -> None:
        """Mock emergency disconnect - logs action"""
        self._values.clear()
        self._approval_log.append({
            "action": "EMERGENCY_DISCONNECT",
            "timestamp": datetime.now()
        })
        # In real implementation: wipe local data and notify hubs