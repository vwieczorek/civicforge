#!/usr/bin/env python3
"""Test board invites with workaround for initial board owner setup."""

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
            return e.code, {'detail': str(error_data)}

def test_invite_system():
    """Test the invite system comprehensively."""
    print("🔧 Testing Board Invite System (Deployment Check)")
    print(f"API URL: {API_URL}")
    
    results = []
    
    # First, let's login as the admin user that should exist
    print("\n1️⃣ Attempting to login as admin...")
    status, admin_data = make_request('POST', '/api/auth/login', {
        'username': 'admin',
        'password': 'admin123'
    })
    
    if status != 200:
        print(f"❌ Failed to login as admin: {admin_data}")
        print("\n⚠️  The deployment may not have the expected admin user")
        print("   Let's test what we can with new users...")
        
        # Register a new organizer
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        status, owner_data = make_request('POST', '/api/auth/register', {
            'username': f'test_organizer_{timestamp}',
            'email': f'test_organizer_{timestamp}@test.com',
            'password': 'testpass123',
            'real_name': 'Test Organizer',
            'role': 'Organizer'
        })
        
        if status != 200:
            print(f"❌ Failed to create organizer: {owner_data}")
            return
        
        admin_token = owner_data['token']
        admin_username = owner_data['username']
        print(f"✅ Created new organizer: {admin_username}")
    else:
        admin_token = admin_data['token']
        admin_username = admin_data['username']
        print(f"✅ Logged in as admin: {admin_username}")
    
    # Check board membership
    print("\n2️⃣ Checking board membership...")
    status, members = make_request('GET', f'/api/boards/{BOARD_ID}/members', token=admin_token)
    
    if status == 200:
        print(f"✅ Can list board members ({len(members)} total)")
        has_owner = False
        for member in members:
            print(f"   - {member['username']} ({member['role']})")
            if member['role'] == 'owner':
                has_owner = True
        
        if has_owner:
            results.append("✅ Board has an owner")
        else:
            results.append("❌ Board has no owner - migrations may not have run correctly")
    else:
        results.append(f"❌ Cannot list members: {status} - {members}")
    
    # Test health check
    print("\n3️⃣ Testing health endpoint...")
    status, health = make_request('GET', '/api/health')
    if status == 200 and health.get('status') == 'healthy':
        results.append("✅ Health check passes")
    else:
        results.append(f"❌ Health check failed: {status} - {health}")
    
    # Test creating a quest (basic functionality)
    print("\n4️⃣ Testing quest creation...")
    status, quest_data = make_request('POST', '/api/quests', {
        'title': f'Test Quest {datetime.now().strftime("%H:%M:%S")}',
        'description': 'Testing deployment functionality',
        'experience_points': 10,
        'status': 'available'
    }, token=admin_token)
    
    if status == 200:
        results.append("✅ Can create quests")
    else:
        results.append(f"❌ Cannot create quests: {status} - {quest_data}")
    
    # Test if we can at least try to create an invite (even if it fails due to permissions)
    print("\n5️⃣ Testing invite endpoint availability...")
    status, invite_response = make_request('POST', f'/api/boards/{BOARD_ID}/invites', {
        'role': 'friend',
        'max_uses': 1,
        'expires_in_hours': 24
    }, token=admin_token)
    
    if status == 200:
        results.append("✅ Admin can create invites!")
        print(f"   Invite token: {invite_response.get('token', 'N/A')[:8]}...")
    elif status == 403:
        results.append("⚠️  Admin cannot create invites (not a board owner)")
    else:
        results.append(f"❌ Unexpected invite response: {status} - {invite_response}")
    
    # Summary
    print("\n📊 Deployment Check Summary:")
    for result in results:
        print(f"   {result}")
    
    passed = sum(1 for r in results if r.startswith("✅"))
    warnings = sum(1 for r in results if r.startswith("⚠️"))
    failed = sum(1 for r in results if r.startswith("❌"))
    
    print(f"\n✅ Passed: {passed}")
    print(f"⚠️  Warnings: {warnings}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\n🔧 Recommendation:")
        print("   The deployment appears to be missing initial board ownership.")
        print("   You may need to:")
        print("   1. Force a new deployment to re-run migrations")
        print("   2. Or manually add the first organizer as board owner")
    
    return failed == 0

if __name__ == '__main__':
    success = test_invite_system()
    sys.exit(0 if success else 1)