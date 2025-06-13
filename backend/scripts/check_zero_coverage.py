#!/usr/bin/env python3
"""
Script to detect zero coverage in critical modules and fail CI/CD
This prevents the "over-mocking" problem from being deployed
"""

import json
import sys
import os

def check_coverage_report():
    """Check if any critical modules have 0% coverage"""
    
    # Critical modules that should never have 0% coverage
    CRITICAL_MODULES = [
        'src/routers/quests_actions.py',
        'src/routers/quests_attest.py',
        'src/routers/quests_create.py',
        'src/routers/quests_delete.py',
        'src/routers/quests_read.py',
        'src/routers/system.py',
        'src/routers/users.py',
        'src/auth.py', 
        'src/db.py'
    ]
    
    # Look for coverage report
    coverage_file = 'coverage.json'
    if not os.path.exists(coverage_file):
        # Try alternate location
        coverage_file = 'htmlcov/status.json'
        if not os.path.exists(coverage_file):
            print("❌ No coverage report found. Run: pytest --cov=src --cov-report=json")
            return False
    
    try:
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Could not parse coverage report: {e}")
        return False
    
    # Check for zero coverage in critical modules
    zero_coverage_modules = []
    missing_modules = []
    
    files_data = coverage_data.get('files', {})
    
    # Check which critical modules are present in coverage report
    for critical_module in CRITICAL_MODULES:
        if critical_module not in files_data:
            missing_modules.append(critical_module)
    
    # Check coverage for modules that are present
    for file_path, file_data in files_data.items():
        if file_path in CRITICAL_MODULES:
            coverage_percent = file_data.get('summary', {}).get('percent_covered', 0)
            if coverage_percent == 0:
                zero_coverage_modules.append(file_path)
    
    if missing_modules:
        print("🚨 CRITICAL: Some critical modules are not being tested at all!")
        print("These modules are not even present in the coverage report:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nThis means the test suite is not importing/executing these modules.")
        
    if zero_coverage_modules:
        print("🚨 CRITICAL: Zero coverage detected in critical modules!")
        print("This usually means you're over-mocking and preventing code execution.")
        print("\nModules with 0% coverage:")
        for module in zero_coverage_modules:
            print(f"  - {module}")
        
    if missing_modules or zero_coverage_modules:
        print("\n💡 SOLUTION:")
        print("  1. Use integration tests with TestClient + moto")
        print("  2. Use app.dependency_overrides instead of @patch")
        print("  3. Let real code execute, only mock external services")
        print("  4. Ensure test fixtures include all routers")
        print("  5. See TESTING_GUIDELINES.md for examples")
        
        return False
    
    print("✅ All critical modules have test coverage")
    return True


def check_overall_coverage():
    """Check if overall coverage meets minimum threshold"""
    
    coverage_file = 'coverage.json'
    if not os.path.exists(coverage_file):
        # Try alternate location
        coverage_file = 'htmlcov/status.json'
        if not os.path.exists(coverage_file):
            return True  # Skip if no report
    
    try:
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)
        
        overall_percent = coverage_data.get('totals', {}).get('percent_covered', 0)
        
        if overall_percent < 70:
            print(f"📊 Overall coverage: {overall_percent:.1f}% (target: 70%)")
            print("Need more tests to reach deployment readiness")
            return False
        
        print(f"✅ Overall coverage: {overall_percent:.1f}% (meets 70% target)")
        return True
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Could not check overall coverage: {e}")
        return True  # Don't fail on parsing errors


if __name__ == "__main__":
    print("🧪 Checking test coverage quality...")
    
    critical_ok = check_coverage_report()
    overall_ok = check_overall_coverage()
    
    if not critical_ok or not overall_ok:
        print("\n❌ Coverage check FAILED")
        sys.exit(1)
    
    print("\n✅ Coverage check PASSED")
    sys.exit(0)