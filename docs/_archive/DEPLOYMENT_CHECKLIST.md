# CivicForge Deployment Checklist

> **Note:** For a comprehensive deployment roadmap with team assignments and timelines, see [MVP_DEPLOYMENT_PLAN.md](./MVP_DEPLOYMENT_PLAN.md)

## Pre-Deployment Verification

### 1. Code Quality ✓
- [ ] All tests are passing (`npm test` in root directory)
- [x] Backend test coverage meets minimum (85.43% current, 70% required)
- [ ] Frontend test coverage meets minimum (~25% current, 70% required) **[See TESTING_STATUS.md]**
  - [x] Critical E2E tests implemented (auth, quest lifecycle, attestation, rewards)
  - [ ] Component unit tests migrated to MSW (QuestList, QuestDetail, QuestAttestationForm, UserProfile)
- [ ] No ESLint errors or warnings
- [ ] All TypeScript types are properly defined

### 2. Security Review ✓
- [ ] No hardcoded secrets or API keys in code
- [ ] All API endpoints have proper authentication
- [ ] CORS is properly configured (no wildcards in production)
- [ ] Input validation is in place for all user inputs
- [ ] SQL injection and XSS protections are active

### 3. Git Status ✓
- [ ] All changes are committed
- [ ] Working on `main` branch (for production)
- [ ] All feature branches have been merged
- [ ] Git tags created for release version
- [ ] No merge conflicts exist

### 4. Infrastructure Configuration ✓
- [ ] All required SSM parameters are set for target stage:
  - `/civicforge/{stage}/cognito-user-pool-id`
  - `/civicforge/{stage}/cognito-app-client-id`
  - `/civicforge/{stage}/frontend-url`
- [ ] DynamoDB tables will be created automatically
- [ ] CloudWatch log groups are configured
- [ ] IAM roles have least-privilege permissions

### 5. Environment Variables ✓
- [ ] Backend environment variables verified in `serverless.yml`
- [ ] Frontend environment variables set for build
- [ ] Feature flags configured appropriately for stage
- [ ] API Gateway throttling limits set

## Deployment Steps

### 1. Pre-Deployment
```bash
# 1. Ensure you're on the correct branch
git checkout main
git pull origin main

# 2. Run all tests
npm test

# 3. Check for uncommitted changes
git status

# 4. Verify AWS credentials
aws sts get-caller-identity
```

### 2. Deploy to Staging First
```bash
# Always test in staging before production
./scripts/deploy.sh staging

# Test the staging deployment
curl https://staging-api.civicforge.example.com/health

# Run smoke tests against staging
npm run test:e2e -- --env=staging
```

### 3. Production Deployment
```bash
# Deploy to production (requires confirmation)
./scripts/deploy.sh prod

# Monitor CloudWatch logs during deployment
aws logs tail /aws/lambda/civicforge-api-prod-api --follow
```

## Post-Deployment Verification

### 1. API Health Checks ✓
- [ ] Health endpoint returns 200 OK
- [ ] Authentication is working (test login)
- [ ] Create a test quest
- [ ] Claim and complete the test quest
- [ ] Verify rewards are distributed

### 2. Frontend Verification ✓
- [ ] Site loads without errors
- [ ] Login/logout flow works
- [ ] Quest creation UI functions
- [ ] Quest list displays properly
- [ ] User profile shows correct data

### 3. Monitoring Setup ✓
- [ ] CloudWatch alarms are active
- [ ] Error rate alarm (> 1% triggers alert)
- [ ] Failed rewards alarm (> 0 abandoned rewards)
- [ ] API latency alarm (> 1000ms p99)
- [ ] DynamoDB throttling alarm

### 4. Database Verification ✓
- [ ] DynamoDB tables created successfully
- [ ] Indexes are active and queryable
- [ ] Backup configuration enabled
- [ ] Point-in-time recovery enabled for production

## Rollback Plan

### Immediate Rollback (< 5 minutes)
```bash
# Backend rollback
cd backend
serverless rollback --stage prod --timestamp <timestamp>

# Frontend rollback (if needed)
# Redeploy previous version from git
git checkout <previous-tag>
./scripts/deploy.sh prod
```

### Data Recovery
- DynamoDB point-in-time recovery enabled
- Can restore to any point in last 35 days
- Failed rewards table maintains history for audit

## Emergency Contacts

- **On-Call Engineer**: [Your contact]
- **AWS Support**: [Support case URL]
- **Monitoring Dashboard**: [CloudWatch dashboard URL]

## Known Issues & Workarounds

1. **Cold Start Latency**: First request after deployment may be slow
   - Workaround: Use provisioned concurrency for production

2. **CloudFront Cache**: Changes may take up to 15 minutes to propagate
   - Workaround: Use cache invalidation for critical updates

3. **DynamoDB Throttling**: May occur during traffic spikes
   - Workaround: Auto-scaling is configured, monitor CloudWatch

## MVP Readiness Verification

### Go/No-Go Criteria (Must complete all):
- [ ] Frontend test coverage ≥ 70% achieved
- [ ] All critical path E2E tests passing
- [ ] Zero critical security vulnerabilities
- [ ] Successful staging deployment with rollback test completed
- [ ] Operational runbook reviewed by on-call team
- [ ] Monitoring dashboards showing healthy metrics
- [ ] Alerts tested and confirmed working

### Sign-Off

Before deploying to production, ensure all stakeholders have signed off:

- [ ] Engineering Lead: ___________________ Date: ___________
- [ ] Security Review: ___________________ Date: ___________
- [ ] Product Owner: ____________________ Date: ___________
- [ ] Operations Lead: ___________________ Date: ___________

## Deployment Log

| Date | Version | Deployed By | Stage | Notes |
|------|---------|-------------|-------|-------|
| | | | | |
| | | | | |
| | | | | |