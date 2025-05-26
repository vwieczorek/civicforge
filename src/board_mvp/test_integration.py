#!/usr/bin/env python3
"""Integration tests to verify core functionality with themes."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_core_api_with_themes():
    """Test that core API endpoints still work with themed interface."""
    print("Testing Core API Integration...")
    
    # Test auth endpoints
    print("Testing authentication...")
    
    # Try to login with test account
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if resp.status_code == 200:
        print("✓ Login endpoint works")
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
    else:
        print("✗ Login failed - creating test user")
        # Try to register
        resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "test123",
            "real_name": "Test User",
            "role": "Organizer"
        })
        if resp.status_code == 200:
            print("✓ Registration works")
            token = resp.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"✗ Registration failed: {resp.status_code}")
            return False
    
    # Test quest endpoints
    print("\nTesting quest endpoints...")
    
    # Get quests
    resp = requests.get(f"{BASE_URL}/api/quests")
    assert resp.status_code == 200
    print("✓ Get quests works")
    
    # Get categories
    resp = requests.get(f"{BASE_URL}/api/categories")
    assert resp.status_code == 200
    print("✓ Get categories works")
    
    # Get user info
    resp = requests.get(f"{BASE_URL}/api/me", headers=headers)
    assert resp.status_code == 200
    user = resp.json()
    print(f"✓ Get user info works (logged in as {user['username']})")
    
    # Get user XP
    resp = requests.get(f"{BASE_URL}/api/users/{user['id']}/experience", headers=headers)
    assert resp.status_code == 200
    xp = resp.json()["experience_balance"]
    print(f"✓ Get XP works (balance: {xp})")
    
    # Get board stats
    resp = requests.get(f"{BASE_URL}/api/stats/board", headers=headers)
    assert resp.status_code == 200
    print("✓ Board stats work")
    
    return True

def test_themed_pages_functionality():
    """Test that themed pages maintain functionality."""
    print("\nTesting Themed Page Functionality...")
    
    session = requests.Session()
    
    # Test login form submission
    resp = session.post(f"{BASE_URL}/login", data={
        "username": "admin",
        "password": "admin123"
    }, allow_redirects=False)
    
    if resp.status_code == 303:  # Redirect after login
        print("✓ Login form submission works")
    else:
        # Try registration
        resp = session.post(f"{BASE_URL}/register", data={
            "username": "testuser2",
            "email": "test2@example.com", 
            "password": "test123",
            "real_name": "Test User 2",
            "role": "Participant"
        }, allow_redirects=False)
        
        if resp.status_code == 303:
            print("✓ Registration form submission works")
        else:
            print(f"✗ Form submission failed: {resp.status_code}")
            return False
    
    # Test main page loads with auth
    resp = session.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    assert "Create Quest" in resp.text
    print("✓ Authenticated main page loads")
    
    # Test stats page
    resp = session.get(f"{BASE_URL}/stats")
    assert resp.status_code == 200
    assert "Board Statistics" in resp.text
    print("✓ Stats page loads")
    
    # Test theme marketplace
    resp = session.get(f"{BASE_URL}/themes")
    assert resp.status_code == 200
    assert "Theme Marketplace" in resp.text
    print("✓ Theme marketplace loads")
    
    return True

def run_integration_tests():
    """Run all integration tests."""
    print("🔧 CivicForge Integration Tests (with Themes)\n")
    
    try:
        resp = requests.get(BASE_URL)
        if resp.status_code != 200:
            print("❌ Server not running")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        return False
    
    all_passed = True
    
    tests = [
        test_core_api_with_themes,
        test_themed_pages_functionality
    ]
    
    for test in tests:
        try:
            if not test():
                all_passed = False
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ All integration tests passed!")
        print("\nCore functionality verified:")
        print("- Authentication system ✓")
        print("- Quest management ✓")
        print("- XP system ✓")
        print("- Statistics ✓")
        print("- Theme system ✓")
    else:
        print("❌ Some integration tests failed")
    
    return all_passed

if __name__ == "__main__":
    run_integration_tests()