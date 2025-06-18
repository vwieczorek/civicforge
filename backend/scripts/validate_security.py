#!/usr/bin/env python3
"""
Security Validation Script for CivicForge
=========================================

"Security is not a product, but a process" - Bruce Schneier

This script validates that all known security vulnerabilities
have been properly addressed in our dependencies.
"""

import subprocess
import sys
import json
from typing import Dict, List, Tuple

# Minimum secure versions for critical packages
SECURITY_REQUIREMENTS = {
    "python-multipart": "0.0.18",
    "requests": "2.32.4",
    "urllib3": "2.5.0",
    "starlette": "0.40.0",
    "fastapi": "0.115.0",  # Compatible with starlette>=0.40.0
}

# Packages that should NOT be present (replaced by alternatives)
FORBIDDEN_PACKAGES = [
    "python-jose",  # Use PyJWT instead
]


def get_installed_packages() -> Dict[str, str]:
    """Get all installed packages and their versions."""
    result = subprocess.run(
        ["pip", "list", "--format=json"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error getting package list: {result.stderr}")
        sys.exit(1)
    
    packages = json.loads(result.stdout)
    return {pkg["name"]: pkg["version"] for pkg in packages}


def parse_version(version: str) -> Tuple[int, ...]:
    """Parse version string into tuple for comparison."""
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        # Handle versions with additional metadata
        base_version = version.split("+")[0].split("-")[0]
        return tuple(int(x) for x in base_version.split("."))


def check_security_requirements(installed: Dict[str, str]) -> List[str]:
    """Check if security requirements are met."""
    issues = []
    
    for package, min_version in SECURITY_REQUIREMENTS.items():
        if package not in installed:
            issues.append(f"❌ {package} is not installed (minimum: {min_version})")
        else:
            installed_version = installed[package]
            if parse_version(installed_version) < parse_version(min_version):
                issues.append(
                    f"❌ {package} {installed_version} is below minimum secure version {min_version}"
                )
            else:
                print(f"✅ {package} {installed_version} meets security requirements")
    
    return issues


def check_forbidden_packages(installed: Dict[str, str]) -> List[str]:
    """Check for packages that should not be installed."""
    issues = []
    
    for package in FORBIDDEN_PACKAGES:
        if package in installed:
            issues.append(
                f"❌ {package} should not be installed (use PyJWT for JWT handling)"
            )
        else:
            print(f"✅ {package} is not installed (good)")
    
    return issues


def run_pip_audit() -> bool:
    """Run pip-audit to check for known vulnerabilities."""
    print("\n🔍 Running pip-audit for vulnerability scanning...")
    
    result = subprocess.run(
        ["pip-audit", "--desc"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ No known vulnerabilities found by pip-audit")
        return True
    else:
        print("❌ Vulnerabilities found:")
        print(result.stdout)
        return False


def main():
    """Main validation function."""
    print("🧘 CivicForge Security Validation")
    print("=" * 50)
    print('"In the pursuit of security, vigilance is the price of peace."\n')
    
    # Get installed packages
    installed = get_installed_packages()
    
    # Check security requirements
    print("📋 Checking security requirements...")
    security_issues = check_security_requirements(installed)
    
    # Check forbidden packages
    print("\n🚫 Checking for forbidden packages...")
    forbidden_issues = check_forbidden_packages(installed)
    
    # Run pip-audit
    audit_passed = run_pip_audit()
    
    # Summary
    all_issues = security_issues + forbidden_issues
    
    print("\n" + "=" * 50)
    if not all_issues and audit_passed:
        print("🎉 All security checks passed!")
        print("Your dependencies are secure and ready for deployment.")
        return 0
    else:
        print("⚠️  Security issues found:")
        for issue in all_issues:
            print(f"  {issue}")
        
        if not audit_passed:
            print("\n⚠️  pip-audit found vulnerabilities (see above)")
        
        print("\n💡 Zen wisdom: 'Security is a journey, not a destination.'")
        print("   Update your requirements.txt and run 'pip install -r requirements.txt'")
        return 1


if __name__ == "__main__":
    sys.exit(main())