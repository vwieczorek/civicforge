"""
API tests for the secure invite system
"""

import pytest
import requests
from datetime import datetime, timedelta
import time
import os

BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')


class TestInviteAPI:
    """Test suite for invite-related API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and authenticate"""
        # Register owner user
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": "test_owner_invites",
            "email": "owner_invites@test.com",
            "password": "testpass123",
            "real_name": "Test Owner",
            "role": "Organizer"
        })
        if resp.status_code == 200:
            self.owner_token = resp.json()["token"]
        else:
            # Login if already exists
            resp = requests.post(f"{BASE_URL}/api/auth/login", json={
                "username": "test_owner_invites",
                "password": "testpass123"
            })
            self.owner_token = resp.json()["token"]
        
        # Register participant user
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": "test_participant_invites",
            "email": "participant_invites@test.com",
            "password": "testpass123",
            "real_name": "Test Participant",
            "role": "Participant"
        })
        if resp.status_code == 200:
            self.participant_token = resp.json()["token"]
        else:
            resp = requests.post(f"{BASE_URL}/api/auth/login", json={
                "username": "test_participant_invites",
                "password": "testpass123"
            })
            self.participant_token = resp.json()["token"]
    
    def test_create_basic_invite(self):
        """Test creating a basic invite with default settings"""
        resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"role": "reviewer"}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert "invite_url" in data
        assert data["role"] == "reviewer"
        assert "expires_at" in data
        
        # Verify expiration is ~48 hours from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        expected_expiry = datetime.now() + timedelta(hours=48)
        assert abs((expires_at - expected_expiry).total_seconds()) < 60  # Within 1 minute
    
    def test_create_custom_invite(self):
        """Test creating invite with custom parameters"""
        resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={
                "role": "friend",
                "email": "specific@user.com",
                "max_uses": 5,
                "expires_hours": 12
            }
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "friend"
        
        # Extract token from URL
        token = data["invite_url"].split("token=")[1]
        assert len(token) > 20  # Should be a long secure token
    
    def test_unauthorized_invite_creation(self):
        """Test that participants cannot create invites"""
        resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.participant_token}"},
            json={"role": "friend"}
        )
        
        assert resp.status_code == 403
        assert "No permission to create invites" in resp.json()["detail"]
    
    def test_accept_valid_invite(self):
        """Test accepting a valid invite"""
        # First create an invite
        create_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"role": "reviewer"}
        )
        token = create_resp.json()["invite_url"].split("token=")[1]
        
        # Register a new user to accept the invite
        reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"new_reviewer_{int(time.time())}",
            "email": f"reviewer_{int(time.time())}@test.com",
            "password": "testpass123",
            "real_name": "New Reviewer"
        })
        new_user_token = reg_resp.json()["token"]
        
        # Accept the invite
        accept_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {new_user_token}"},
            json={"token": token}
        )
        
        assert accept_resp.status_code == 200
        assert accept_resp.json()["role"] == "reviewer"
    
    def test_invite_single_use_enforcement(self):
        """Test that single-use invites can only be used once"""
        # Create single-use invite
        create_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"role": "friend", "max_uses": 1}
        )
        token = create_resp.json()["invite_url"].split("token=")[1]
        
        # First user accepts
        user1_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"user1_{int(time.time())}",
            "email": f"user1_{int(time.time())}@test.com",
            "password": "testpass123",
            "real_name": "User 1"
        })
        user1_token = user1_resp.json()["token"]
        
        accept1_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"token": token}
        )
        assert accept1_resp.status_code == 200
        
        # Second user tries to accept
        user2_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"user2_{int(time.time())}",
            "email": f"user2_{int(time.time())}@test.com",
            "password": "testpass123",
            "real_name": "User 2"
        })
        user2_token = user2_resp.json()["token"]
        
        accept2_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {user2_token}"},
            json={"token": token}
        )
        assert accept2_resp.status_code == 400
        assert "already used" in accept2_resp.json()["detail"]
    
    def test_invalid_invite_token(self):
        """Test using an invalid invite token"""
        resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {self.participant_token}"},
            json={"token": "INVALID_TOKEN_12345"}
        )
        
        assert resp.status_code == 404
        assert "Invalid invite" in resp.json()["detail"]
    
    def test_list_board_members(self):
        """Test listing board members"""
        resp = requests.get(
            f"{BASE_URL}/api/boards/board_001/members",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        
        assert resp.status_code == 200
        members = resp.json()
        assert isinstance(members, list)
        
        # Should have at least the owner
        assert any(m["role"] in ["owner", "organizer"] for m in members)
    
    def test_remove_member(self):
        """Test removing a board member"""
        # First add a member via invite
        create_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"role": "friend"}
        )
        token = create_resp.json()["invite_url"].split("token=")[1]
        
        # Register and accept
        reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"removable_user_{int(time.time())}",
            "email": f"remove_{int(time.time())}@test.com",
            "password": "testpass123",
            "real_name": "Removable User"
        })
        user_token = reg_resp.json()["token"]
        user_id = reg_resp.json()["user_id"]
        
        requests.post(
            f"{BASE_URL}/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"token": token}
        )
        
        # Remove the member
        remove_resp = requests.delete(
            f"{BASE_URL}/api/boards/board_001/members/{user_id}",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        
        assert remove_resp.status_code == 200
        
        # Verify they're removed
        members_resp = requests.get(
            f"{BASE_URL}/api/boards/board_001/members",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        members = members_resp.json()
        assert not any(m["user_id"] == user_id for m in members)
    
    def test_cannot_remove_without_permission(self):
        """Test that non-owners cannot remove members"""
        resp = requests.delete(
            f"{BASE_URL}/api/boards/board_001/members/999",
            headers={"Authorization": f"Bearer {self.participant_token}"}
        )
        
        assert resp.status_code == 403
        assert "No permission to manage members" in resp.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])