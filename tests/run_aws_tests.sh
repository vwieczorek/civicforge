#!/bin/bash
# Run tests against AWS deployment

set -e

# Configuration
export API_BASE_URL=${API_BASE_URL:-"http://YOUR_AWS_IP:8000"}
export TEST_ENV="aws-production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}CivicForge Secure Access System Test Suite${NC}"
echo -e "${BLUE}===============================================${NC}"

# Check if API_BASE_URL is set properly
if [[ "$API_BASE_URL" == *"YOUR_AWS_IP"* ]]; then
    echo -e "${RED}ERROR: Please set API_BASE_URL to your AWS deployment URL${NC}"
    echo -e "${YELLOW}Example: export API_BASE_URL=http://54.123.45.67:8000${NC}"
    exit 1
fi

echo -e "${GREEN}Testing against: $API_BASE_URL${NC}"

# Check if the API is accessible
echo -e "\n${YELLOW}1. Checking API health...${NC}"
if curl -s -f "$API_BASE_URL/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API is not accessible at $API_BASE_URL${NC}"
    exit 1
fi

# Install test dependencies if needed
echo -e "\n${YELLOW}2. Installing test dependencies...${NC}"
pip install -q pytest requests

# Run API tests
echo -e "\n${YELLOW}3. Running invite API tests...${NC}"
cd /Users/victor/Projects/civicforge
python -m pytest tests/api/test_invites.py -v --tb=short

# Run RBAC permission tests
echo -e "\n${YELLOW}4. Running RBAC permission tests...${NC}"
python -m pytest tests/permissions/test_rbac.py -v --tb=short

# Quick security test
echo -e "\n${YELLOW}5. Running basic security tests...${NC}"
echo -e "${BLUE}Testing unauthorized access...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/boards/board_001/members" | tail -n 1)
if [ "$RESPONSE" = "401" ]; then
    echo -e "${GREEN}✓ Unauthorized access properly blocked (401)${NC}"
else
    echo -e "${RED}✗ Unexpected response code: $RESPONSE${NC}"
fi

echo -e "${BLUE}Testing invalid invite token...${NC}"
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"token": "INVALID_TOKEN_12345"}' \
    -w "\n%{http_code}" \
    "$API_BASE_URL/api/boards/board_001/join" | tail -n 1)
if [ "$RESPONSE" = "401" ]; then
    echo -e "${GREEN}✓ Invalid token properly rejected (401)${NC}"
else
    echo -e "${RED}✗ Unexpected response code: $RESPONSE${NC}"
fi

# Summary
echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}===============================================${NC}"

# Count test results (this is a simplified version)
TOTAL_TESTS=$(grep -c "PASSED\|FAILED" pytest_output.log 2>/dev/null || echo "0")
PASSED_TESTS=$(grep -c "PASSED" pytest_output.log 2>/dev/null || echo "0")
FAILED_TESTS=$(grep -c "FAILED" pytest_output.log 2>/dev/null || echo "0")

if [ "$FAILED_TESTS" = "0" ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed. Please check the output above.${NC}"
fi

echo -e "\n${GREEN}Test execution complete!${NC}"