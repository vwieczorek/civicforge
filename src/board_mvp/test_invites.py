#!/usr/bin/env python3
"""Test board invites and access control."""

import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

API_URL = os.environ.get('API_URL', 'http://localhost:8000')
BOARD_ID = 'board_001'

def make_request(method, path, data=None, token=None):
    """Make HTTP request to API."""
    url = f"{API_URL}{path}"
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode('utf-8')
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_data = e.read()
        try:
            return e.code, json.loads(error_data.decode('utf-8'))
        except:
            return e.code, {'detail': 'Unknown error'}

def test_invite_system():
    """Test the invite system comprehensively."""
    print("🔧 Testing Board Invite System")
    print(f"API URL: {API_URL}")
    
    results = []
    
    # 1. Create test users via registration
    print("\n1️⃣ Creating test users...")
    
    # Register owner (first organizer)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    status, owner_data = make_request('POST', '/api/auth/register', {
        'username': f'test_owner_invites_{timestamp}',
        'email': f'test_owner_{timestamp}@test.com',
        'password': 'testpass123',
        'real_name': 'Test Owner',
        'role': 'Organizer'
    })
    if status != 200:
        print(f"❌ Failed to create owner: {owner_data}")
        return
    owner_token = owner_data['token']
    owner_id = owner_data['user_id']
    print(f"✅ Created owner: {owner_data['username']}")
    
    # Register friend user
    status, friend_data = make_request('POST', '/api/auth/register', {
        'username': f'test_friend_{timestamp}',
        'email': f'test_friend_{timestamp}@test.com',
        'password': 'testpass123',
        'real_name': 'Test Friend',
        'role': 'Friend'
    })
    if status != 200:
        print(f"❌ Failed to create friend: {friend_data}")
        return
    friend_token = friend_data['token']
    print(f"✅ Created friend: {friend_data['username']}")
    
    # Wait a moment for database to settle
    import time
    time.sleep(1)
    
    # 2. Check if owner is board member
    print("\n2️⃣ Checking board membership...")
    status, members = make_request('GET', f'/api/boards/{BOARD_ID}/members', token=owner_token)
    if status == 200:
        print(f"   Found {len(members)} board members")
        owner_is_member = False
        for member in members:
            print(f"   - {member['username']} ({member['role']})")
            if member['user_id'] == owner_id:
                owner_is_member = True
        
        if not owner_is_member:
            print("   ⚠️  Owner is not automatically a board member. This may cause permission issues.")
    else:
        print(f"   Failed to check members: {status} - {members}")
    
    # 3. Test unauthorized invite creation
    print("\n3️⃣ Testing unauthorized invite creation...")
    status, data = make_request('POST', f'/api/boards/{BOARD_ID}/invites', {
        'role': 'friend',
        'max_uses': 1,
        'expires_in_hours': 24
    }, token=friend_token)
    
    if status == 403:
        results.append("✅ Unauthorized user cannot create invites")
    else:
        results.append(f"❌ Expected 403, got {status}: {data}")
    
    # 4. Test owner creating invite
    print("\n4️⃣ Testing owner creating invite...")
    status, invite_data = make_request('POST', f'/api/boards/{BOARD_ID}/invites', {
        'role': 'friend',
        'max_uses': 2,
        'expires_in_hours': 24
    }, token=owner_token)
    
    if status == 200:
        results.append("✅ Owner can create invites")
        invite_token = invite_data['token']
        print(f"   Created invite token: {invite_token[:8]}...")
    else:
        results.append(f"❌ Owner failed to create invite: {status} - {invite_data}")
        print("\n🔍 Debugging: Let me check if this is a first-time setup issue...")
        
        # Try to manually add owner as board member
        print("   Attempting to manually setup board owner...")
        # This would need admin access, so we'll note it for the summary
        print("   ⚠️  The deployment may need to run migrations to set up initial board ownership")
        return results
    
    # 5. Test joining with invalid token
    print("\n5️⃣ Testing join with invalid token...")
    status, data = make_request('POST', f'/api/boards/{BOARD_ID}/join', {
        'invite_token': 'invalid-token-12345'
    }, token=friend_token)
    
    if status == 404:
        results.append("✅ Invalid token is rejected")
    else:
        results.append(f"❌ Expected 404, got {status}: {data}")
    
    # 6. Test joining with valid token
    print("\n6️⃣ Testing join with valid token...")
    status, data = make_request('POST', f'/api/boards/{BOARD_ID}/join', {
        'invite_token': invite_token
    }, token=friend_token)
    
    if status == 200:
        results.append("✅ User can join with valid token")
    else:
        results.append(f"❌ Failed to join with valid token: {status} - {data}")
    
    # 7. Test listing members
    print("\n7️⃣ Testing member listing...")
    status, members = make_request('GET', f'/api/boards/{BOARD_ID}/members', token=owner_token)
    
    if status == 200:
        results.append(f"✅ Can list members ({len(members)} members)")
        for member in members:
            print(f"   - {member['username']} ({member['role']})")
    else:
        results.append(f"❌ Failed to list members: {status} - {members}")
    
    # 8. Test friend permissions
    print("\n8️⃣ Testing friend permissions...")
    status, data = make_request('POST', f'/api/boards/{BOARD_ID}/invites', {
        'role': 'participant',
        'max_uses': 1
    }, token=friend_token)
    
    if status == 403:
        results.append("✅ Friend cannot create invites")
    else:
        results.append(f"❌ Friend should not be able to create invites: {status}")
    
    # 9. Test removing member
    print("\n9️⃣ Testing member removal...")
    # Get friend's user ID
    friend_id = None
    if members and isinstance(members, list):  # From previous member listing
        for member in members:
            if member['username'] == friend_data['username']:
                friend_id = member['user_id']
                break
    
    if friend_id:
        status, data = make_request('DELETE', f'/api/boards/{BOARD_ID}/members/{friend_id}', token=owner_token)
        
        if status == 200:
            results.append("✅ Owner can remove members")
        else:
            results.append(f"❌ Failed to remove member: {status} - {data}")
    else:
        print("   ⚠️  Could not find friend in member list to test removal")
    
    # 10. Test token expiration/max uses
    print("\n🔟 Testing token limits...")
    # Create new friend for this test
    status, friend2_data = make_request('POST', '/api/auth/register', {
        'username': f'test_friend2_{timestamp}',
        'email': f'test_friend2_{timestamp}@test.com',
        'password': 'testpass123',
        'real_name': 'Test Friend 2',
        'role': 'Friend'
    })
    
    if status == 200 and invite_token:
        # Try to use the same token again (should fail if max_uses was enforced)
        status, data = make_request('POST', f'/api/boards/{BOARD_ID}/join', {
            'invite_token': invite_token
        }, token=friend2_data['token'])
        
        if status in [400, 404]:
            results.append("✅ Token use limits are enforced")
        else:
            results.append(f"❌ Token should be exhausted: {status}")
    
    # Print summary
    print("\n📊 Test Results Summary:")
    for result in results:
        print(f"   {result}")
    
    passed = sum(1 for r in results if r.startswith("✅"))
    total = len(results)
    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} tests passed")
    
    return passed == total

if __name__ == '__main__':
    success = test_invite_system()
    sys.exit(0 if success else 1)