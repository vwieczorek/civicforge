#!/bin/bash
# MVP Readiness Check Script for CivicForge

echo "🔍 CivicForge MVP Readiness Check"
echo "================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize counters
PASSED=0
FAILED=0

# Function to check a condition
check() {
    local description=$1
    local condition=$2
    
    if eval "$condition"; then
        echo -e "${GREEN}✅${NC} $description"
        ((PASSED++))
    else
        echo -e "${RED}❌${NC} $description"
        ((FAILED++))
    fi
}

# Frontend View Checks
echo -e "\n📱 Frontend Views:"
check "Quest List View exists" "[ -f frontend/src/views/QuestList.tsx ]"
check "Quest Detail View exists" "[ -f frontend/src/views/QuestDetail.tsx ]"
check "Create Quest Form exists" "[ -f frontend/src/views/CreateQuest.tsx ]"
check "User Profile Page exists" "[ -f frontend/src/views/UserProfile.tsx ]"

# API Endpoint Checks (by searching routes.py)
echo -e "\n🔌 API Endpoints:"
check "GET /quests endpoint exists" "grep -q '@router.get(\"/quests\"' backend/src/routes.py"
check "GET /users/{user_id} endpoint exists" "grep -q '@router.get(\"/users/' backend/src/routes.py"
check "DELETE /quests/{quest_id} endpoint exists" "grep -q '@router.delete(\"/quests/' backend/src/routes.py"

# Security Measures
echo -e "\n🔒 Security Measures:"
check "Input validation in models" "grep -q '@validator' backend/src/models.py"
check "Atomic claim_quest operation" "grep -q 'claim_quest_atomic' backend/src/db.py"
check "Atomic submit_quest operation" "grep -q 'submit_quest_atomic' backend/src/db.py"
check "Atomic delete_quest operation" "grep -q 'delete_quest_atomic' backend/src/db.py"
check "XSS prevention in QuestCreate" "grep -q 'regex=.*<>.*' backend/src/models.py"
check "Authorization check in claim" "grep -q 'Cannot claim your own quest' backend/src/routes.py"

# Economy & Anti-Spam
echo -e "\n💰 Economy & Anti-Spam:"
check "Quest creation points system" "grep -q 'questCreationPoints' backend/src/models.py"
check "Points deduction on creation" "grep -q 'deduct_quest_points' backend/src/routes.py"
check "Points award on completion" "grep -q 'award_quest_points' backend/src/routes.py"
check "Server-side reward calculation" "grep -q 'updated_quest.rewardXp' backend/src/routes.py"

# Test Coverage (if tests exist)
echo -e "\n🧪 Test Coverage:"
if [ -d "backend/tests" ]; then
    TEST_COUNT=$(find backend/tests -name "test_*.py" | wc -l | tr -d ' ')
    if [ "$TEST_COUNT" -gt 3 ]; then
        echo -e "${GREEN}✅${NC} Found $TEST_COUNT test files"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️${NC} Only $TEST_COUNT test files found (recommend more)"
        ((FAILED++))
    fi
else
    echo -e "${RED}❌${NC} No tests directory found"
    ((FAILED++))
fi

# Environment Setup
echo -e "\n⚙️  Environment Configuration:"
check "Backend serverless.yml exists" "[ -f backend/serverless.yml ]"
check "Frontend package.json exists" "[ -f frontend/package.json ]"
check "AWS Amplify configured" "grep -q 'Amplify.configure' frontend/src/App.tsx"

# Documentation
echo -e "\n📚 Documentation:"
check "README.md exists" "[ -f README.md ]"
check "DEVELOPMENT.md exists" "[ -f DEVELOPMENT.md ]"
check "ARCHITECTURE.md exists" "[ -f ARCHITECTURE.md ]"
check "MVP plan in DEVELOPMENT.md" "grep -q 'MVP Deployment Readiness' DEVELOPMENT.md"

# Final Summary
echo -e "\n================================="
echo -e "📊 Summary:"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

TOTAL=$((PASSED + FAILED))
PERCENTAGE=$((PASSED * 100 / TOTAL))

echo -e "\nMVP Readiness: ${PERCENTAGE}%"

if [ $PERCENTAGE -ge 90 ]; then
    echo -e "${GREEN}✅ Project is ready for MVP deployment!${NC}"
    exit 0
elif [ $PERCENTAGE -ge 70 ]; then
    echo -e "${YELLOW}⚠️  Project is almost ready. Address remaining issues.${NC}"
    exit 1
else
    echo -e "${RED}❌ Project needs more work before MVP deployment.${NC}"
    exit 1
fi