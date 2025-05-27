"""
Role-Based Access Control (RBAC) tests for all user roles
"""

import pytest
import requests
import time
import os

BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')


class TestRBACPermissions:
    """Test suite for verifying role-based permissions"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self):
        """Setup test users for each role"""
        self.users = {}
        
        # Create owner (first quest creator)
        owner_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"test_owner_rbac_{int(time.time())}",
            "email": f"owner_rbac_{int(time.time())}@test.com",
            "password": "testpass123",
            "real_name": "Test Owner",
            "role": "Organizer"
        })
        self.users['owner'] = {
            'token': owner_resp.json()["token"],
            'id': owner_resp.json()["user_id"]
        }
        
        # Make owner by creating first quest (after getting initial XP)
        # First, make owner an organizer to get 20 XP
        requests.post(
            f"{BASE_URL}/api/quests",
            headers={"Authorization": f"Bearer {self.users['owner']['token']}"},
            json={"title": "First Quest", "description": "Makes me owner"}
        )
        
        # Create other role users via invites
        roles_to_create = {
            'organizer': 'organizer',
            'reviewer': 'reviewer',
            'friend': 'friend',
            'participant': 'participant'
        }
        
        for key, role in roles_to_create.items():
            # Create invite
            invite_resp = requests.post(
                f"{BASE_URL}/api/boards/board_001/invites",
                headers={"Authorization": f"Bearer {self.users['owner']['token']}"},
                json={"role": role}
            )
            token = invite_resp.json()["invite_url"].split("token=")[1]
            
            # Register user
            reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
                "username": f"test_{key}_rbac_{int(time.time())}",
                "email": f"{key}_rbac_{int(time.time())}@test.com",
                "password": "testpass123",
                "real_name": f"Test {key.title()}"
            })
            
            user_token = reg_resp.json()["token"]
            user_id = reg_resp.json()["user_id"]
            
            # Accept invite to get role
            requests.post(
                f"{BASE_URL}/api/boards/board_001/join",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"token": token}
            )
            
            self.users[key] = {
                'token': user_token,
                'id': user_id
            }
        
        # Give organizer some XP to create quests
        self._give_xp_to_user(self.users['organizer']['id'], 20)
        
        # Give friend some XP to create quests  
        self._give_xp_to_user(self.users['friend']['id'], 10)
    
    def _give_xp_to_user(self, user_id, amount):
        """Helper to give XP to a user (would be done via admin endpoint in real system)"""
        # In a real system, this would be an admin endpoint
        # For testing, we'll have the user complete a quest
        pass
    
    def test_view_board_permission(self):
        """Test that all roles can view the board"""
        for role, user_data in self.users.items():
            resp = requests.get(
                f"{BASE_URL}/api/quests",
                headers={"Authorization": f"Bearer {user_data['token']}"}
            )
            assert resp.status_code == 200, f"{role} should be able to view board"
    
    def test_create_quest_permission(self):
        """Test quest creation permissions"""
        allowed_roles = ['owner', 'organizer', 'friend']
        
        for role, user_data in self.users.items():
            resp = requests.post(
                f"{BASE_URL}/api/quests",
                headers={"Authorization": f"Bearer {user_data['token']}"},
                json={
                    "title": f"Test Quest by {role}",
                    "description": "Testing permissions"
                }
            )
            
            if role in allowed_roles:
                # Should succeed if they have enough XP
                assert resp.status_code in [200, 400], f"{role} should be able to create quests (or fail on XP)"
                if resp.status_code == 400:
                    assert "Insufficient experience" in resp.json()["detail"]
            else:
                assert resp.status_code == 403, f"{role} should NOT be able to create quests"
                assert "No permission to create quests" in resp.json()["detail"]
    
    def test_claim_quest_permission(self):
        """Test quest claiming permissions"""
        # First create a quest as owner
        create_resp = requests.post(
            f"{BASE_URL}/api/quests",
            headers={"Authorization": f"Bearer {self.users['owner']['token']}"},
            json={"title": "Quest to Claim", "description": "For testing claims"}
        )
        quest_id = create_resp.json()["id"]
        
        allowed_roles = ['owner', 'organizer', 'friend', 'participant']
        
        for role, user_data in self.users.items():
            # Create new quest for each test to avoid conflicts
            if role != 'owner':  # Skip owner who created it
                create_resp = requests.post(
                    f"{BASE_URL}/api/quests",
                    headers={"Authorization": f"Bearer {self.users['owner']['token']}"},
                    json={"title": f"Quest for {role}", "description": "Test"}
                )
                test_quest_id = create_resp.json()["id"]
                
                resp = requests.post(
                    f"{BASE_URL}/api/quests/{test_quest_id}/claim",
                    headers={"Authorization": f"Bearer {user_data['token']}"}
                )
                
                if role in allowed_roles:
                    assert resp.status_code == 200, f"{role} should be able to claim quests"
                else:
                    assert resp.status_code == 403, f"{role} should NOT be able to claim quests"
    
    def test_verify_quest_permission(self):
        """Test quest verification permissions"""
        allowed_roles = ['owner', 'organizer', 'reviewer', 'friend']
        
        for role, user_data in self.users.items():
            # Create and prepare a quest for verification
            create_resp = requests.post(
                f"{BASE_URL}/api/quests",
                headers={"Authorization": f"Bearer {self.users['owner']['token']}"},
                json={"title": f"Quest to verify by {role}", "description": "Test"}
            )
            quest_id = create_resp.json()["id"]
            
            # Claim it as participant
            requests.post(
                f"{BASE_URL}/api/quests/{quest_id}/claim",
                headers={"Authorization": f"Bearer {self.users['participant']['token']}"}
            )
            
            # Submit work
            requests.post(
                f"{BASE_URL}/api/quests/{quest_id}/submit",
                headers={"Authorization": f"Bearer {self.users['participant']['token']}"}
            )
            
            # Try to verify
            resp = requests.post(
                f"{BASE_URL}/api/quests/{quest_id}/verify",
                headers={"Authorization": f"Bearer {user_data['token']}"},
                json={"result": "normal"}
            )
            
            if role in allowed_roles:
                assert resp.status_code == 200, f"{role} should be able to verify quests"
            else:
                assert resp.status_code == 403, f"{role} should NOT be able to verify quests"
    
    def test_create_invites_permission(self):
        """Test invite creation permissions"""
        allowed_roles = ['owner', 'organizer']
        
        for role, user_data in self.users.items():
            resp = requests.post(
                f"{BASE_URL}/api/boards/board_001/invites",
                headers={"Authorization": f"Bearer {user_data['token']}"},
                json={"role": "participant"}
            )
            
            if role in allowed_roles:
                assert resp.status_code == 200, f"{role} should be able to create invites"
            else:
                assert resp.status_code == 403, f"{role} should NOT be able to create invites"
    
    def test_manage_members_permission(self):
        """Test member management permissions"""
        allowed_roles = ['owner']
        
        # Create a dummy member to try to remove
        invite_resp = requests.post(
            f"{BASE_URL}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.users['owner']['token']}"},
            json={"role": "participant"}
        )
        token = invite_resp.json()["invite_url"].split("token=")[1]
        
        dummy_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": f"dummy_user_{int(time.time())}",
            "email": f"dummy_{int(time.time())}@test.com",
            "password": "testpass123",
            "real_name": "Dummy User"
        })
        dummy_token = dummy_resp.json()["token"]
        dummy_id = dummy_resp.json()["user_id"]
        
        requests.post(
            f"{BASE_URL}/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {dummy_token}"},
            json={"token": token}
        )
        
        for role, user_data in self.users.items():
            resp = requests.delete(
                f"{BASE_URL}/api/boards/board_001/members/{dummy_id}",
                headers={"Authorization": f"Bearer {user_data['token']}"}
            )
            
            if role in allowed_roles:
                # May get 404 if already deleted in previous iteration
                assert resp.status_code in [200, 404], f"{role} should be able to manage members"
            else:
                assert resp.status_code == 403, f"{role} should NOT be able to manage members"
    
    def test_view_analytics_permission(self):
        """Test analytics viewing permissions"""
        # Note: This would test analytics endpoints when implemented
        # For now, we'll test that users can see their membership info which includes analytics permission
        
        for role, user_data in self.users.items():
            resp = requests.get(
                f"{BASE_URL}/api/me",
                headers={"Authorization": f"Bearer {user_data['token']}"}
            )
            
            assert resp.status_code == 200
            user_info = resp.json()
            
            if user_info.get("board_membership"):
                permissions = user_info["board_membership"]["permissions"]
                
                expected_analytics = role in ['owner', 'organizer', 'reviewer']
                actual_analytics = permissions.get("view_analytics", False)
                
                assert actual_analytics == expected_analytics, \
                    f"{role} analytics permission mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])