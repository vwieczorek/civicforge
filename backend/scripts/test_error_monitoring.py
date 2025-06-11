#!/usr/bin/env python3
"""
Test script to verify API error monitoring is working correctly.
This simulates various error conditions to ensure CloudWatch alarms trigger properly.
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_error_monitoring(api_url: str):
    """Test various error scenarios to verify monitoring"""
    
    print(f"\n🔍 Testing error monitoring for API at: {api_url}")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "404 Not Found",
            "method": "GET",
            "path": "/api/v1/nonexistent",
            "expected_status": 404
        },
        {
            "name": "401 Unauthorized",
            "method": "POST",
            "path": "/api/v1/quests",
            "headers": {},  # No auth header
            "expected_status": 401
        },
        {
            "name": "422 Validation Error",
            "method": "POST",
            "path": "/api/v1/quests",
            "headers": {"Authorization": "Bearer invalid_token"},
            "json": {"invalid": "data"},  # Missing required fields
            "expected_status": 422
        },
        {
            "name": "Method Not Allowed",
            "method": "DELETE",
            "path": "/api/v1/quests",
            "headers": {"Authorization": "Bearer invalid_token"},
            "expected_status": 405
        }
    ]
    
    errors_generated = 0
    
    for test in test_cases:
        print(f"\n📍 Test: {test['name']}")
        
        try:
            response = requests.request(
                method=test["method"],
                url=f"{api_url}{test['path']}",
                headers=test.get("headers", {}),
                json=test.get("json")
            )
            
            print(f"   Status: {response.status_code} (expected: {test['expected_status']})")
            
            if response.status_code == test["expected_status"]:
                print("   ✅ Test passed")
                errors_generated += 1
            else:
                print(f"   ❌ Unexpected status code")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")
    
    print(f"\n📊 Summary: Generated {errors_generated} errors")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    
    if errors_generated >= 5:
        print("\n✅ SUCCESS: Generated enough errors to trigger CloudWatch alarm (threshold: 5)")
        print("   Check CloudWatch console in ~5 minutes to verify alarm triggered")
    else:
        print(f"\n⚠️  WARNING: Only generated {errors_generated} errors (need 5+ to trigger alarm)")
        print("   Running additional error requests...")
        
        # Generate additional errors to reach threshold
        for i in range(5 - errors_generated):
            try:
                requests.get(f"{api_url}/api/v1/trigger/error/{i}")
            except:
                pass
            time.sleep(0.5)
        
        print("   ✅ Additional errors generated to reach threshold")
    
    print("\n📝 Next steps:")
    print("1. Wait 5 minutes for CloudWatch to aggregate metrics")
    print("2. Check CloudWatch Alarms console for 'civicforge-{stage}-api-errors'")
    print("3. Verify alarm is in ALARM state")
    print("4. Check CloudWatch Logs for structured error logs")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_error_monitoring.py <api_url>")
        print("Example: python test_error_monitoring.py https://api.dev.civicforge.com")
        sys.exit(1)
    
    test_error_monitoring(sys.argv[1])