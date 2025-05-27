#!/usr/bin/env python3
"""Test member removal functionality."""

import os
import sys
import json
import urllib.request
import urllib.error
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
            return e.code, {'detail': str(error_data)}

def test_member_removal():
    """Test the member removal functionality."""
    print("🔧 Testing Member Removal")
    print(f"API URL: {API_URL}")
    
    # Login as admin
    print("\n1️⃣ Logging in as admin...")
    status, admin_data = make_request('POST', '/api/auth/login', {
        'username': 'admin',
        'password': 'admin123'
    })
    
    if status != 200:
        print(f"❌ Failed to login: {admin_data}")
        return False
    
    admin_token = admin_data['token']
    print("✅ Logged in as admin")
    
    # Create a test user
    print("\n2️⃣ Creating test user...")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    status, user_data = make_request('POST', '/api/auth/register', {
        'username': f'test_removal_{timestamp}',
        'email': f'test_removal_{timestamp}@test.com',
        'password': 'testpass123',
        'real_name': 'Test Removal User',
        'role': 'Friend'
    })
    
    if status != 200:
        print(f"❌ Failed to create user: {user_data}")
        return False
    
    user_token = user_data['token']
    user_id = user_data['user_id']
    print(f"✅ Created user: {user_data['username']} (ID: {user_id})")
    
    # Create and use invite
    print("\n3️⃣ Creating invite for test user...")
    status, invite_data = make_request('POST', f'/api/boards/{BOARD_ID}/invites', {
        'role': 'friend',
        'max_uses': 1
    }, token=admin_token)
    
    if status != 200:
        print(f"❌ Failed to create invite: {invite_data}")
        return False
    
    invite_token = invite_data['invite_url'].split('token=')[1]
    print(f"✅ Created invite: {invite_token[:8]}...")
    
    # Join board
    print("\n4️⃣ User joining board...")
    status, join_data = make_request('POST', f'/api/boards/{BOARD_ID}/join', {
        'token': invite_token
    }, token=user_token)
    
    if status != 200:
        print(f"❌ Failed to join: {join_data}")
        return False
    
    print("✅ User joined board")
    
    # List members to confirm
    print("\n5️⃣ Listing board members...")
    status, members = make_request('GET', f'/api/boards/{BOARD_ID}/members', token=admin_token)
    
    if status == 200:
        print(f"✅ Found {len(members)} members:")
        for member in members:
            print(f"   - {member['username']} (ID: {member['user_id']}, Role: {member['role']})")
    
    # Remove the test user
    print(f"\n6️⃣ Removing test user (ID: {user_id})...")
    status, remove_data = make_request('DELETE', f'/api/boards/{BOARD_ID}/members/{user_id}', token=admin_token)
    
    if status == 200:
        print("✅ Successfully removed member!")
        print(f"   Response: {remove_data}")
    else:
        print(f"❌ Failed to remove member: {status} - {remove_data}")
        return False
    
    # Verify removal
    print("\n7️⃣ Verifying member was removed...")
    status, members_after = make_request('GET', f'/api/boards/{BOARD_ID}/members', token=admin_token)
    
    if status == 200:
        removed = True
        for member in members_after:
            if member['user_id'] == user_id:
                removed = False
                break
        
        if removed:
            print(f"✅ Confirmed: User removed (now {len(members_after)} members)")
        else:
            print("❌ User still appears in member list!")
            return False
    
    return True

if __name__ == '__main__':
    success = test_member_removal()
    sys.exit(0 if success else 1)