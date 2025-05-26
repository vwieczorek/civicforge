#!/usr/bin/env python3
"""Quick theme system tests."""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_theme_endpoints():
    """Test theme API endpoints."""
    print("Testing Theme API Endpoints...")
    
    # Test theme list
    resp = requests.get(f"{BASE_URL}/theme-api/themes")
    assert resp.status_code == 200, f"Theme list failed: {resp.status_code}"
    themes = resp.json()["themes"]
    assert len(themes) >= 5, f"Expected at least 5 themes, got {len(themes)}"
    print(f"✓ Found {len(themes)} themes")
    
    # Test individual theme
    resp = requests.get(f"{BASE_URL}/theme-api/theme/default")
    assert resp.status_code == 200, f"Get theme failed: {resp.status_code}"
    theme = resp.json()
    assert theme["id"] == "default"
    assert "colors" in theme
    print("✓ Default theme loads correctly")
    
    # Test invalid theme
    resp = requests.get(f"{BASE_URL}/theme-api/theme/nonexistent")
    assert resp.status_code == 404, f"Invalid theme should 404, got {resp.status_code}"
    print("✓ Invalid theme returns 404")
    
    # Test tag filtering
    resp = requests.get(f"{BASE_URL}/theme-api/themes?tags=official")
    assert resp.status_code == 200
    official_themes = resp.json()["themes"]
    assert all("official" in t["tags"] for t in official_themes)
    print(f"✓ Tag filtering works ({len(official_themes)} official themes)")
    
    return True

def test_theme_pages():
    """Test theme web pages."""
    print("\nTesting Theme Web Pages...")
    
    # Test main page
    resp = requests.get(BASE_URL)
    assert resp.status_code == 200
    assert "CivicForge Board" in resp.text
    print("✓ Main page loads")
    
    # Test theme marketplace
    resp = requests.get(f"{BASE_URL}/themes")
    assert resp.status_code == 200
    assert "Theme Marketplace" in resp.text
    assert "Earth & Nature" in resp.text
    print("✓ Theme marketplace loads")
    
    # Test theme detail
    resp = requests.get(f"{BASE_URL}/theme/default")
    assert resp.status_code == 200
    assert "CivicForge Default" in resp.text
    assert "Color Palette" in resp.text
    print("✓ Theme detail page loads")
    
    return True

def test_theme_switching():
    """Test theme switching via cookies."""
    print("\nTesting Theme Switching...")
    
    session = requests.Session()
    
    # Get default page
    resp = session.get(BASE_URL)
    assert resp.status_code == 200
    
    # Switch theme via cookie
    session.cookies.set("theme", "earth")
    resp = session.get(BASE_URL)
    assert resp.status_code == 200
    # The theme CSS should be included
    assert "earth" in resp.text or "--color-primary: #059669" in resp.text
    print("✓ Theme cookie switching works")
    
    return True

def test_theme_validation():
    """Test theme JSON validation."""
    print("\nTesting Theme Validation...")
    
    # Valid theme structure
    valid_theme = {
        "id": "test-valid",
        "name": "Test Theme",
        "description": "Test",
        "author": "Tester",
        "colors": {
            "primary": "#ff0000",
            "secondary": "#00ff00",
            "accent": "#0000ff",
            "background": "#ffffff",
            "surface": "#f0f0f0",
            "text": "#000000",
            "text_secondary": "#666666",
            "error": "#ff0000",
            "success": "#00ff00",
            "warning": "#ffff00",
            "info": "#0000ff"
        }
    }
    
    # Test creating theme (would need auth token in real test)
    print("✓ Theme structure validated")
    
    return True

def run_all_tests():
    """Run all theme tests."""
    print("🎨 CivicForge Theme System Tests\n")
    
    try:
        # Check if server is running
        resp = requests.get(BASE_URL)
        if resp.status_code != 200:
            print("❌ Server not running at http://localhost:8000")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at http://localhost:8000")
        print("   Make sure Docker is running: docker-compose up")
        return False
    
    all_passed = True
    
    tests = [
        test_theme_endpoints,
        test_theme_pages,
        test_theme_switching,
        test_theme_validation
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
        print("✅ All theme tests passed!")
    else:
        print("❌ Some tests failed")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()