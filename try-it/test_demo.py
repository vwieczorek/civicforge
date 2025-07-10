#!/usr/bin/env python3
"""Quick test to verify CivicForge demo is working

To run this test:
1. Ensure the API is running (e.g., via ./launch_demo.sh)
2. Execute: ../src/venv/bin/python3 test_demo.py
"""

try:
    import requests
except ModuleNotFoundError:
    print("❌ 'requests' library not found.")
    print("   Please run this test using the project's virtual environment:")
    print("   ../src/venv/bin/python3 test_demo.py")
    exit(1)

import sys

def test_api():
    """Test if API is running and healthy"""
    try:
        # Test health endpoint (public)
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is {data['status']}")
            print(f"   Redis: {data['services']['redis']}")
            print(f"   Auth: {data['services']['auth']}")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Please start the API with: cd ../src && ./venv/bin/python -m api.main_with_auth")
        return False

def test_auth_required():
    """Test that protected endpoints require authentication"""
    try:
        response = requests.get("http://localhost:8000/api/me")
        if response.status_code == 403:
            print("✅ Authentication is properly enforced")
            return True
        else:
            print(f"⚠️  Protected endpoint returned {response.status_code} without auth")
            return False
    except Exception as e:
        print(f"❌ Error testing protected endpoint: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing CivicForge Demo Setup")
    print("=" * 40)
    
    if not test_api():
        sys.exit(1)
    
    print()
    if not test_auth_required():
        sys.exit(1)
    
    print("\n✅ Demo is ready to run!")
    print("   Use: python civic_demo.py")
    print("   Or:  python demo_auth.py (for detailed auth flow)")