# AWS Deployment Test Plan for Secure Access System

## Test Environment Setup

### Prerequisites
- AWS deployment URL (e.g., https://civicforge.example.com)
- Test user accounts with different roles
- API testing tool (Postman/curl)
- Browser automation tool (Selenium/Playwright) for UI tests
- Load testing tool (JMeter/Locust)

### Test Data
```yaml
test_users:
  owner:
    username: test_owner
    email: owner@test.com
    role: Organizer  # Will become owner by creating first quest
  
  organizer:
    username: test_organizer
    email: organizer@test.com
    role: Organizer
  
  reviewer:
    username: test_reviewer
    email: reviewer@test.com
    role: Participant  # Will be upgraded via invite
  
  friend:
    username: test_friend
    email: friend@test.com
    role: Participant  # Will be upgraded via invite
  
  participant:
    username: test_participant
    email: participant@test.com
    role: Participant
```

## 1. Functional Tests

### 1.1 Invite Creation Tests

```bash
# Test 1.1.1: Create invite with default settings
curl -X POST https://civicforge.example.com/api/boards/board_001/invites \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "reviewer"
  }'
# Expected: 200 OK, invite_url returned, expires_at = now + 48 hours

# Test 1.1.2: Create invite with custom expiration
curl -X POST https://civicforge.example.com/api/boards/board_001/invites \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "friend",
    "expires_hours": 24,
    "max_uses": 5
  }'
# Expected: 200 OK, multi-use invite created

# Test 1.1.3: Create invite with email restriction
curl -X POST https://civicforge.example.com/api/boards/board_001/invites \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "reviewer",
    "email": "specific@reviewer.com"
  }'
# Expected: 200 OK, email-restricted invite created
```

### 1.2 Invite Acceptance Tests

```bash
# Test 1.2.1: Accept valid invite
curl -X POST https://civicforge.example.com/api/boards/board_001/join \
  -H "Authorization: Bearer $NEW_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "VALID_INVITE_TOKEN"
  }'
# Expected: 200 OK, membership created

# Test 1.2.2: Attempt to use expired invite
# Create invite with 1-hour expiration, wait 2 hours, then:
curl -X POST https://civicforge.example.com/api/boards/board_001/join \
  -H "Authorization: Bearer $NEW_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "EXPIRED_INVITE_TOKEN"
  }'
# Expected: 400 Bad Request, "Invite expired"

# Test 1.2.3: Attempt to exceed max uses
# Use a single-use invite twice
# Expected: 400 Bad Request on second use
```

### 1.3 Membership Management Tests

```bash
# Test 1.3.1: List board members
curl -X GET https://civicforge.example.com/api/boards/board_001/members \
  -H "Authorization: Bearer $OWNER_TOKEN"
# Expected: 200 OK, array of members with roles

# Test 1.3.2: Remove member
curl -X DELETE https://civicforge.example.com/api/boards/board_001/members/$USER_ID \
  -H "Authorization: Bearer $OWNER_TOKEN"
# Expected: 200 OK, member removed

# Test 1.3.3: Attempt to remove last owner
curl -X DELETE https://civicforge.example.com/api/boards/board_001/members/$OWNER_ID \
  -H "Authorization: Bearer $OWNER_TOKEN"
# Expected: 400 Bad Request, "Cannot remove the only board owner"
```

## 2. Permission Verification Tests

### 2.1 Role-Based Access Matrix

| Action | Owner | Organizer | Reviewer | Friend | Participant | Non-Member |
|--------|-------|-----------|----------|--------|-------------|------------|
| View Board | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Create Quest | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Claim Quest | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ |
| Verify Quest | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Create Invites | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Manage Members | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

### 2.2 Permission Test Scripts

```python
# Test 2.2.1: Verify each role's permissions
import requests

def test_role_permissions(base_url, role, token):
    tests = {
        'create_quest': lambda: requests.post(
            f"{base_url}/api/quests",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Quest", "description": "Test"}
        ),
        'claim_quest': lambda: requests.post(
            f"{base_url}/api/quests/1/claim",
            headers={"Authorization": f"Bearer {token}"}
        ),
        'verify_quest': lambda: requests.post(
            f"{base_url}/api/quests/1/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"result": "normal"}
        ),
        'create_invite': lambda: requests.post(
            f"{base_url}/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "friend"}
        ),
        'manage_members': lambda: requests.delete(
            f"{base_url}/api/boards/board_001/members/999",
            headers={"Authorization": f"Bearer {token}"}
        )
    }
    
    expected_permissions = {
        'owner': ['create_quest', 'claim_quest', 'verify_quest', 'create_invite', 'manage_members'],
        'organizer': ['create_quest', 'claim_quest', 'verify_quest', 'create_invite'],
        'reviewer': ['verify_quest'],
        'friend': ['create_quest', 'claim_quest', 'verify_quest'],
        'participant': ['claim_quest']
    }
    
    for action, test_func in tests.items():
        response = test_func()
        should_succeed = action in expected_permissions.get(role, [])
        
        if should_succeed:
            assert response.status_code in [200, 201], f"{role} should have {action} permission"
        else:
            assert response.status_code == 403, f"{role} should NOT have {action} permission"
```

## 3. Security Tests

### 3.1 Authentication Tests

```bash
# Test 3.1.1: Access without token
curl -X GET https://civicforge.example.com/api/boards/board_001/members
# Expected: 401 Unauthorized

# Test 3.1.2: Access with invalid token
curl -X GET https://civicforge.example.com/api/boards/board_001/members \
  -H "Authorization: Bearer INVALID_TOKEN"
# Expected: 401 Unauthorized

# Test 3.1.3: Access with expired token
# Use token older than 24 hours
# Expected: 401 Unauthorized
```

### 3.2 Invite Security Tests

```bash
# Test 3.2.1: Attempt SQL injection in invite token
curl -X POST https://civicforge.example.com/api/boards/board_001/join \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "'; DROP TABLE board_invites; --"
  }'
# Expected: 404 Not Found (invalid invite)

# Test 3.2.2: Attempt to create invite without permission
curl -X POST https://civicforge.example.com/api/boards/board_001/invites \
  -H "Authorization: Bearer $PARTICIPANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "owner"
  }'
# Expected: 403 Forbidden

# Test 3.2.3: Attempt to join with someone else's email-restricted invite
# Create invite for specific@email.com, try to use with different user
# Expected: 400 Bad Request
```

## 4. Web UI Tests

### 4.1 Invite Flow UI Tests

```javascript
// Using Playwright for browser automation
const { test, expect } = require('@playwright/test');

test('Complete invite flow', async ({ page }) => {
  // Test 4.1.1: Create invite via UI
  await page.goto('https://civicforge.example.com/login');
  await page.fill('input[name="username"]', 'test_owner');
  await page.fill('input[name="password"]', 'password');
  await page.click('button[type="submit"]');
  
  await page.goto('https://civicforge.example.com/invites');
  await page.selectOption('select[name="role"]', 'reviewer');
  await page.fill('input[name="email"]', 'new.reviewer@test.com');
  await page.click('button:has-text("Create Invite")');
  
  // Verify invite URL is displayed
  await expect(page.locator('.success')).toContainText('Invite created!');
  
  // Test 4.1.2: Accept invite flow
  const inviteUrl = await page.locator('.success').textContent();
  const match = inviteUrl.match(/https:\/\/[^\s]+/);
  
  // Open in new incognito context
  const context = await browser.newContext();
  const newPage = await context.newPage();
  await newPage.goto(match[0]);
  
  // Should see login prompt
  await expect(newPage.locator('h1')).toContainText('Join Board');
  await newPage.click('a:has-text("login")');
  
  // Login and auto-redirect to accept
  await newPage.fill('input[name="username"]', 'new_user');
  await newPage.fill('input[name="password"]', 'password');
  await newPage.click('button[type="submit"]');
  
  // Should redirect to board with success message
  await expect(newPage.locator('.success')).toContainText('Successfully joined board!');
});
```

### 4.2 Permission UI Tests

```javascript
test('UI elements respect permissions', async ({ page }) => {
  // Test 4.2.1: Participant shouldn't see Invites link
  await loginAs(page, 'test_participant', 'password');
  await page.goto('https://civicforge.example.com/');
  await expect(page.locator('a:has-text("Invites")')).not.toBeVisible();
  
  // Test 4.2.2: Organizer should see Invites link
  await loginAs(page, 'test_organizer', 'password');
  await page.goto('https://civicforge.example.com/');
  await expect(page.locator('a:has-text("Invites")')).toBeVisible();
  
  // Test 4.2.3: Reviewer can't create quests
  await loginAs(page, 'test_reviewer', 'password');
  await page.goto('https://civicforge.example.com/');
  await expect(page.locator('form#create-quest-form')).not.toBeVisible();
});
```

## 5. Load and Performance Tests

### 5.1 Concurrent Invite Usage

```python
# Using Locust for load testing
from locust import HttpUser, task, between

class InviteLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Create a multi-use invite (max_uses=100)
        response = self.client.post("/api/auth/login", json={
            "username": "test_owner",
            "password": "password"
        })
        self.token = response.json()["token"]
        
        invite_response = self.client.post(
            "/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"role": "friend", "max_uses": 100}
        )
        self.invite_token = invite_response.json()["invite_url"].split("token=")[1]
    
    @task
    def accept_invite(self):
        # Register new user
        username = f"user_{self.environment.runner.user_count}_{random.randint(1000,9999)}"
        self.client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "password",
            "real_name": "Load Test User"
        })
        
        # Login and accept invite
        login_resp = self.client.post("/api/auth/login", json={
            "username": username,
            "password": "password"
        })
        user_token = login_resp.json()["token"]
        
        self.client.post(
            "/api/boards/board_001/join",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"token": self.invite_token},
            name="/api/boards/[board_id]/join"
        )

# Run with: locust -f invite_load_test.py --host=https://civicforge.example.com --users=50 --spawn-rate=5
```

### 5.2 Performance Benchmarks

```yaml
performance_targets:
  invite_creation:
    p95_response_time: 200ms
    p99_response_time: 500ms
    success_rate: 99.9%
  
  invite_acceptance:
    p95_response_time: 300ms
    p99_response_time: 700ms
    success_rate: 99.9%
  
  member_listing:
    p95_response_time: 150ms
    p99_response_time: 400ms
    success_rate: 99.9%
    
  concurrent_users:
    sustained_load: 100 users
    peak_load: 500 users
    invite_accepts_per_second: 10
```

## 6. Edge Cases and Error Handling

### 6.1 Edge Case Tests

```bash
# Test 6.1.1: Unicode and special characters in invite
curl -X POST https://civicforge.example.com/api/boards/board_001/invites \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "friend",
    "email": "test+特殊文字@example.com"
  }'
# Expected: 200 OK, properly encoded

# Test 6.1.2: Maximum length inputs
# Create invite with very long email (255 chars)
# Expected: 200 OK or 400 with clear error

# Test 6.1.3: Minimum expiration time
curl -X POST https://civicforge.example.com/api/boards/board_001/invites \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "friend",
    "expires_hours": 0
  }'
# Expected: 400 Bad Request, minimum expiration required

# Test 6.1.4: Race condition - simultaneous invite acceptance
# Two users try to use last slot of limited invite simultaneously
# Expected: One succeeds, one fails gracefully
```

### 6.2 Database Consistency Tests

```sql
-- Test 6.2.1: Verify referential integrity
SELECT * FROM board_memberships 
WHERE user_id NOT IN (SELECT id FROM users);
-- Expected: 0 rows

SELECT * FROM board_invites 
WHERE created_by_user_id NOT IN (SELECT id FROM users);
-- Expected: 0 rows

-- Test 6.2.2: Check for duplicate memberships
SELECT board_id, user_id, COUNT(*) 
FROM board_memberships 
GROUP BY board_id, user_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Test 6.2.3: Verify JSON permissions are valid
SELECT * FROM board_memberships 
WHERE permissions NOT LIKE '%view_board%';
-- Expected: 0 rows (all should have at least view permission)
```

## 7. Monitoring and Observability Tests

### 7.1 CloudWatch Metrics

```python
# Test 7.1.1: Verify metrics are being logged
def test_cloudwatch_metrics():
    # Perform various invite operations
    create_invite()
    accept_invite()
    list_members()
    
    # Query CloudWatch
    cloudwatch = boto3.client('cloudwatch')
    response = cloudwatch.get_metric_statistics(
        Namespace='CivicForge',
        MetricName='InviteCreated',
        Dimensions=[{'Name': 'Environment', 'Value': 'production'}],
        StartTime=datetime.now() - timedelta(minutes=5),
        EndTime=datetime.now(),
        Period=300,
        Statistics=['Sum']
    )
    
    assert response['Datapoints'][0]['Sum'] >= 1
```

### 7.2 Error Tracking

```bash
# Test 7.2.1: Verify errors are logged properly
# Trigger various error conditions and check CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/ecs/civicforge \
  --start-time $(date -u -d '5 minutes ago' +%s)000 \
  --filter-pattern "[timestamp, request_id, level=ERROR, message]"
# Expected: Errors are properly formatted and include context
```

## 8. Automated Test Suite

### 8.1 Test Runner Script

```bash
#!/bin/bash
# run_secure_access_tests.sh

set -e

echo "Running CivicForge Secure Access Test Suite"
echo "=========================================="

# Set environment
export API_BASE_URL="https://civicforge.example.com"
export TEST_ENV="aws-production"

# Run API tests
echo "1. Running API tests..."
pytest tests/api/test_invites.py -v

# Run permission tests
echo "2. Running permission tests..."
pytest tests/permissions/test_rbac.py -v

# Run security tests
echo "3. Running security tests..."
pytest tests/security/test_invite_security.py -v

# Run UI tests
echo "4. Running UI tests..."
playwright test tests/ui/invite_flow.spec.js

# Run load tests
echo "5. Running load tests (5 minute duration)..."
locust -f tests/load/invite_load_test.py \
  --host=$API_BASE_URL \
  --users=50 \
  --spawn-rate=5 \
  --run-time=5m \
  --headless \
  --html=load_test_report.html

# Generate report
echo "6. Generating test report..."
python generate_test_report.py

echo "Test suite completed!"
```

### 8.2 CI/CD Integration

```yaml
# .github/workflows/post-deploy-tests.yml
name: Post-Deployment Tests

on:
  workflow_dispatch:
  deployment_status:

jobs:
  test-secure-access:
    if: ${{ github.event.deployment_status.state == 'success' }}
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r tests/requirements.txt
        npx playwright install
    
    - name: Run test suite
      env:
        API_BASE_URL: ${{ github.event.deployment_status.target_url }}
      run: |
        ./tests/run_secure_access_tests.sh
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: |
          test_report.html
          load_test_report.html
          screenshots/
```

## Test Execution Schedule

1. **Immediate Post-Deployment** (Critical Path)
   - Authentication tests
   - Basic invite creation/acceptance
   - Permission verification for each role

2. **Within 1 Hour** (Extended Validation)
   - All functional tests
   - Security tests
   - Edge case tests

3. **Within 24 Hours** (Full Suite)
   - Load tests
   - Performance benchmarks
   - UI automation tests

4. **Ongoing** (Monitoring)
   - CloudWatch metrics validation
   - Error rate monitoring
   - Database consistency checks

## Success Criteria

- All critical path tests pass
- No security vulnerabilities found
- Performance meets defined SLAs
- Error rate < 0.1%
- All user roles can perform their designated actions
- Invite expiration and usage limits enforced correctly