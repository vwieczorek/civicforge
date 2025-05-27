# AWS Test Execution Guide for Secure Access System

## Prerequisites

1. **AWS Deployment**: Ensure CivicForge is deployed to AWS using the deployment guide
2. **AWS CLI**: Configured with appropriate credentials
3. **Python 3.x**: For running pytest
4. **Docker**: For local testing before AWS deployment

## Step 1: Deploy to AWS (if not already deployed)

```bash
# 1. Build and push Docker image
cd /path/to/civicforge
./deploy/aws/deploy.sh

# 2. Wait for deployment to complete
# The script will wait for service stabilization
```

## Step 2: Verify Deployment

```bash
# Run the verification script to get your deployment URL
./verify_deployment.sh

# You should see output like:
# ✓ Deployment found!
# Application URL: http://54.123.45.67:8000
```

## Step 3: Set Test Environment

```bash
# Export the API URL from the verification output
export API_BASE_URL=http://YOUR_AWS_IP:8000

# Example:
export API_BASE_URL=http://54.123.45.67:8000
```

## Step 4: Run Test Suite

```bash
# Run all tests
./tests/run_aws_tests.sh
```

## Step 5: Run Individual Test Categories

### Invite API Tests
```bash
cd /path/to/civicforge
python -m pytest tests/api/test_invites.py -v
```

### RBAC Permission Tests
```bash
python -m pytest tests/permissions/test_rbac.py -v
```

### Manual Security Tests
```bash
# Test 1: Unauthorized access
curl -v $API_BASE_URL/api/boards/board_001/members
# Expected: 401 Unauthorized

# Test 2: SQL injection attempt
curl -X POST $API_BASE_URL/api/boards/board_001/join \
  -H "Content-Type: application/json" \
  -d '{"token": "'; DROP TABLE board_invites; --"}'
# Expected: 404 Not Found

# Test 3: Invalid token format
curl -X POST $API_BASE_URL/api/boards/board_001/join \
  -H "Content-Type: application/json" \
  -d '{"token": "INVALID_TOKEN"}'
# Expected: 401 or 404
```

## Step 6: Load Testing (Optional)

```bash
# Install locust
pip install locust

# Create a simple load test file
cat > invite_load_test.py << 'EOF'
from locust import HttpUser, task, between
import random
import time

class InviteLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Register and login as organizer
        self.client.post("/api/auth/register", json={
            "username": f"loadtest_org_{random.randint(1000,9999)}",
            "email": f"loadtest_{random.randint(1000,9999)}@test.com",
            "password": "testpass123",
            "real_name": "Load Test Organizer",
            "role": "Organizer"
        })
        
    @task
    def create_and_accept_invite(self):
        # Login
        resp = self.client.post("/api/auth/login", json={
            "username": self.username,
            "password": "testpass123"
        })
        token = resp.json()["token"]
        
        # Create invite
        invite_resp = self.client.post(
            "/api/boards/board_001/invites",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "friend", "max_uses": 10}
        )
        
        if invite_resp.status_code == 200:
            # Simulate invite acceptance
            time.sleep(random.uniform(0.5, 2))
EOF

# Run load test
locust -f invite_load_test.py --host=$API_BASE_URL --users=10 --spawn-rate=2 --run-time=2m --headless
```

## Step 7: Monitor Test Results

### CloudWatch Logs
```bash
# View application logs during tests
aws logs tail /ecs/civicforge-board-mvp --follow --region us-east-1
```

### ECS Service Metrics
```bash
# Check service health
aws ecs describe-services \
    --cluster civicforge-cluster \
    --services civicforge-board-service \
    --region us-east-1 \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

## Expected Test Results

### ✅ Passing Tests Should Show:

1. **Invite Creation**
   - Organizers can create invites
   - Proper token generation
   - Correct expiration times

2. **Access Control**
   - Each role has correct permissions
   - Unauthorized actions return 403
   - Invalid tokens return 401/404

3. **Member Management**
   - Owners can remove members
   - Cannot remove last owner
   - Member list is accurate

### ❌ Common Issues and Fixes:

1. **Database Not Initialized**
   ```bash
   # Check if migrations ran
   aws logs filter-log-events \
       --log-group-name /ecs/civicforge-board-mvp \
       --filter-pattern "CREATE TABLE" \
       --region us-east-1
   ```

2. **Environment Variables Missing**
   - Check ECS task definition for DATABASE_URL
   - Verify Secrets Manager configuration

3. **Network Issues**
   - Ensure security groups allow inbound traffic
   - Check if public IP is assigned

## Test Report Generation

After running tests, generate a summary:

```bash
# Create test report
cat > test_report_$(date +%Y%m%d_%H%M%S).md << EOF
# CivicForge Secure Access Test Report
Date: $(date)
Environment: AWS Production
API URL: $API_BASE_URL

## Test Results Summary

### API Tests
$(python -m pytest tests/api/test_invites.py --tb=no -q | tail -n 5)

### RBAC Tests  
$(python -m pytest tests/permissions/test_rbac.py --tb=no -q | tail -n 5)

### Security Tests
- Unauthorized access: ✓ Blocked (401)
- SQL injection: ✓ Prevented (404)
- Invalid tokens: ✓ Rejected (401/404)

### Performance
- API response time: < 200ms (p95)
- Concurrent users supported: 50+

## Recommendations
1. All core functionality working as expected
2. Security measures properly enforced
3. Ready for production use with monitoring

EOF
```

## Continuous Testing

Set up automated testing on deployment:

```yaml
# .github/workflows/post-deploy-test.yml
name: Post-Deployment Tests

on:
  workflow_run:
    workflows: ["Deploy to AWS"]
    types:
      - completed

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Get deployment URL
        run: |
          ./verify_deployment.sh > deployment.txt
          export API_BASE_URL=$(grep "Application URL" deployment.txt | awk '{print $3}')
      - name: Run tests
        run: ./tests/run_aws_tests.sh
```

## Success Criteria

The deployment is considered successful when:

- [ ] All API tests pass (100%)
- [ ] All RBAC tests pass (100%)
- [ ] Security tests show proper access control
- [ ] Application responds within 500ms (p99)
- [ ] No errors in CloudWatch logs
- [ ] Service is stable with desired task count