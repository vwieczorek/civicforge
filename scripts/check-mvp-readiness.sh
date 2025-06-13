#!/bin/bash

# CivicForge MVP Readiness Check Script
# This script verifies all MVP requirements are met before deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo "CivicForge MVP Readiness Check"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall readiness
READY=true

# Function to check test coverage
check_coverage() {
    local component=$1
    local target=$2
    local coverage_file=$3
    
    if [ -f "$coverage_file" ]; then
        # Extract coverage percentage (assumes format like "All files | XX.XX |")
        coverage=$(grep -E "All files.*\|.*\|" "$coverage_file" | awk -F'|' '{print $2}' | tr -d ' %')
        
        if [ -z "$coverage" ]; then
            echo -e "${RED}✗ $component: Unable to determine coverage${NC}"
            READY=false
        else
            if (( $(echo "$coverage >= $target" | bc -l) )); then
                echo -e "${GREEN}✓ $component: $coverage% (target: $target%)${NC}"
            else
                echo -e "${RED}✗ $component: $coverage% (target: $target%)${NC}"
                READY=false
            fi
        fi
    else
        echo -e "${YELLOW}⚠ $component: Coverage report not found${NC}"
        READY=false
    fi
}

echo "1. Checking Test Coverage"
echo "------------------------"

# Run backend tests and check coverage
echo "Running backend tests..."
cd "$PROJECT_ROOT/backend"
if npm test > /dev/null 2>&1; then
    # Backend uses pytest with coverage.json
    if [ -f "coverage.json" ]; then
        coverage=$(python -c "import json; data=json.load(open('coverage.json')); print(data.get('totals', {}).get('percent_covered', 0))")
        if (( $(echo "$coverage >= 70" | bc -l) )); then
            echo -e "${GREEN}✓ Backend: $coverage% (target: 70%)${NC}"
        else
            echo -e "${RED}✗ Backend: $coverage% (target: 70%)${NC}"
            READY=false
        fi
    fi
else
    echo -e "${RED}✗ Backend tests failed${NC}"
    READY=false
fi

# Run frontend tests and check coverage
echo "Running frontend tests..."
cd "$PROJECT_ROOT/frontend"
if npm run coverage > /dev/null 2>&1; then
    # Frontend uses vitest with coverage report
    check_coverage "Frontend" 70 "coverage/coverage-summary.json"
else
    echo -e "${RED}✗ Frontend tests failed${NC}"
    READY=false
fi

echo ""
echo "2. Checking Critical Files"
echo "-------------------------"

# Check for E2E test files
if [ -d "$PROJECT_ROOT/frontend/e2e" ] || [ -d "$PROJECT_ROOT/frontend/tests/e2e" ]; then
    echo -e "${GREEN}✓ E2E test directory found${NC}"
else
    echo -e "${YELLOW}⚠ E2E test directory not found (recommended)${NC}"
fi

# Check for operational runbook
if [ -f "$PROJECT_ROOT/docs/OPERATIONS.md" ]; then
    echo -e "${GREEN}✓ Operational runbook exists${NC}"
else
    echo -e "${RED}✗ Operational runbook missing${NC}"
    READY=false
fi

echo ""
echo "3. Checking Security"
echo "-------------------"

# Check for npm vulnerabilities
cd "$PROJECT_ROOT/frontend"
audit_result=$(npm audit --production 2>&1 || true)
if echo "$audit_result" | grep -q "found 0 vulnerabilities"; then
    echo -e "${GREEN}✓ Frontend: No vulnerabilities${NC}"
else
    critical=$(echo "$audit_result" | grep -oE "[0-9]+ critical" | grep -oE "[0-9]+" || echo "0")
    high=$(echo "$audit_result" | grep -oE "[0-9]+ high" | grep -oE "[0-9]+" || echo "0")
    if [ "$critical" -gt 0 ]; then
        echo -e "${RED}✗ Frontend: $critical critical vulnerabilities found${NC}"
        READY=false
    elif [ "$high" -gt 0 ]; then
        echo -e "${YELLOW}⚠ Frontend: $high high vulnerabilities found${NC}"
    else
        echo -e "${GREEN}✓ Frontend: Only low/moderate vulnerabilities${NC}"
    fi
fi

# Check backend dependencies
cd "$PROJECT_ROOT/backend"
if command -v safety &> /dev/null; then
    if safety check --json > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend: No security vulnerabilities${NC}"
    else
        echo -e "${RED}✗ Backend: Security vulnerabilities found${NC}"
        READY=false
    fi
else
    echo -e "${YELLOW}⚠ Backend: 'safety' not installed, skipping security check${NC}"
fi

echo ""
echo "4. Checking Infrastructure"
echo "-------------------------"

# Check for required SSM parameters
required_params=(
    "/civicforge/staging/cognito-user-pool-id"
    "/civicforge/staging/cognito-app-client-id"
    "/civicforge/staging/frontend-url"
)

echo "Checking SSM parameters..."
for param in "${required_params[@]}"; do
    if aws ssm get-parameter --name "$param" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Found: $param${NC}"
    else
        echo -e "${YELLOW}⚠ Missing: $param (required for staging)${NC}"
    fi
done

echo ""
echo "5. Checking Deployment Scripts"
echo "-----------------------------"

if [ -x "$PROJECT_ROOT/scripts/deploy.sh" ]; then
    echo -e "${GREEN}✓ Deployment script is executable${NC}"
else
    echo -e "${RED}✗ Deployment script not found or not executable${NC}"
    READY=false
fi

if [ -f "$PROJECT_ROOT/scripts/rollback.sh" ] || grep -q "rollback" "$PROJECT_ROOT/scripts/deploy.sh" 2>/dev/null; then
    echo -e "${GREEN}✓ Rollback procedure documented${NC}"
else
    echo -e "${YELLOW}⚠ Rollback procedure not clearly documented${NC}"
fi

echo ""
echo "================================================"
echo "MVP Readiness Summary"
echo "================================================"

if [ "$READY" = true ]; then
    echo -e "${GREEN}✅ All MVP requirements are met!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Deploy to staging: ./scripts/deploy.sh staging"
    echo "2. Run E2E tests in staging"
    echo "3. Perform rollback test"
    echo "4. Get stakeholder sign-offs"
    echo "5. Deploy to production: ./scripts/deploy.sh prod"
else
    echo -e "${RED}❌ MVP requirements not met${NC}"
    echo ""
    echo "Critical blockers:"
    echo "- Frontend test coverage must reach 70%"
    echo ""
    echo "See MVP_DEPLOYMENT_PLAN.md for detailed implementation guide"
fi

echo ""
echo "For detailed test results, run:"
echo "- Backend: cd backend && npm test"
echo "- Frontend: cd frontend && npm run coverage"

exit $([ "$READY" = true ] && echo 0 || echo 1)