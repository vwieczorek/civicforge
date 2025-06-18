# MVP Deployment Plan

## Executive Summary

This document outlines the deployment plan for CivicForge MVP, including current status, blockers, and the path to production deployment.

## Current Status (as of December 16, 2024)

### ✅ Backend - READY
- **Test Coverage**: 85.78% (exceeds 70% requirement)
- **All Tests**: Passing
- **Infrastructure**: Serverless configuration complete
- **Security**: IAM roles and policies configured
- **API**: Fully functional with error handling

### ⚠️ Frontend - IMPROVED BUT STILL BLOCKED
- **Test Status**: **12 of 86 tests failing** (reduced from 23)
- **Test Coverage**: ~25% (below 70% requirement)
- **Components**: Core functionality complete
- **Integration**: WorkSubmissionModal integrated, QuestFilters pending
- **Progress Made**:
  - ✅ Fixed React-hot-toast mock issues
  - ✅ Fixed AWS Amplify auth mocking
  - ✅ Resolved test assertion mismatches
  - ✅ Fixed async handling in tests

### 🚧 Infrastructure
- **AWS Resources**: DynamoDB tables, Lambda functions ready
- **SSM Parameters**: **Missing for staging environment** (critical)
- **E2E Tests**: **Playwright configuration broken**
- **Deployment Scripts**: Available but blocked by tests

## MVP Requirements Checklist

### Functional Requirements
- [x] User registration and authentication
- [x] Quest creation with rewards
- [x] Quest browsing and discovery
- [x] Quest claiming mechanism
- [x] Work submission interface
- [x] Dual-attestation system
- [x] Reputation tracking

### Technical Requirements
- [x] Backend API (85.78% coverage)
- [ ] Frontend tests passing (**12 failing**, down from 23)
- [ ] Frontend coverage ≥70%
- [x] Basic E2E test suite
- [x] Security hardening
- [ ] Deployment automation
- [ ] Operational runbook

### Documentation Requirements
- [x] README with setup instructions
- [x] API documentation
- [x] Testing guide
- [x] Architecture documentation
- [ ] Component documentation (partial)
- [ ] Deployment guide

## Current Blockers

### 1. Frontend Test Failures (CRITICAL - IMPROVING)
**Issue**: **12 tests failing** (reduced from 23)
**Impact**: Still blocks deployments per quality gates
**Components Affected**:
- CreateQuest (act() warnings)
- QuestDetail (edge cases)
- QuestList (API error handling)
- UserProfile (edge case)
- App (Amplify config)
- E2E tests (3 - Playwright config)

**Root Causes Fixed**:
- ✅ React-hot-toast mocking
- ✅ AWS Amplify auth mocking
- ✅ Test assertion text mismatches
- ✅ Async state handling
- ✅ Component data structures

**Remaining Issues**:
- ❌ act() warnings in CreateQuest
- ❌ Amplify configuration in App.test.tsx
- ❌ E2E Playwright configuration

**Next Steps**:
1. Fix act() warnings in CreateQuest tests
2. Resolve App.test.tsx Amplify config issue
3. Debug Playwright configuration for E2E tests
4. Handle remaining edge cases
5. Add tests to increase coverage to 70%

### 2. Frontend Coverage Gap
**Current**: ~25%
**Required**: 70% minimum
**Gap Areas**:
- Error boundary coverage
- Loading state tests
- Edge case handling
- User interaction flows
- Component integration tests

**Priority Areas for New Tests**:
1. Critical user flows (quest creation → attestation)
2. Error handling paths
3. Authentication flows
4. State management edge cases

### 3. Missing Infrastructure
**Staging Environment**:
- `/civicforge/staging/cognito-user-pool-id`
- `/civicforge/staging/cognito-app-client-id`
- `/civicforge/staging/frontend-url`

**Resolution**: Run staging infrastructure setup

## Deployment Sequence

### Phase 1: Fix Frontend Tests (Current Focus)
```bash
# 1. Fix failing tests
cd frontend
npm test -- --run

# 2. Check coverage
npm run coverage

# 3. Verify all tests pass
npm test
```

### Phase 2: Infrastructure Setup
```bash
# 1. Set up staging infrastructure
npm run setup:infra:staging

# 2. Configure SSM parameters
aws ssm put-parameter --name "/civicforge/staging/cognito-user-pool-id" --value "xxx"
aws ssm put-parameter --name "/civicforge/staging/cognito-app-client-id" --value "xxx"
aws ssm put-parameter --name "/civicforge/staging/frontend-url" --value "https://staging.civicforge.com"
```

### Phase 3: Staging Deployment
```bash
# 1. Check readiness
npm run check:mvp

# 2. Deploy to staging
npm run deploy:staging

# 3. Run E2E tests
npm run test:e2e:staging
```

### Phase 4: Production Deployment
```bash
# 1. Final checks
npm run check:mvp

# 2. Deploy to production
npm run deploy:prod

# 3. Smoke tests
npm run test:smoke:prod
```

## Risk Mitigation

### Rollback Strategy
1. **Automatic**: CloudFormation rollback on failure
2. **Manual**: Previous version redeployment
3. **Database**: Point-in-time recovery enabled

### Monitoring
- CloudWatch dashboards configured
- Error alerts set up
- Performance metrics tracked

### Security
- WAF rules configured
- API rate limiting enabled
- Least privilege IAM policies

## Timeline Estimate

### Optimistic (Given current progress)
- Frontend test fixes: 2-3 hours (12 remaining)
- Coverage increase: 2-3 hours
- Infrastructure setup: 30 minutes
- E2E fixes: 1 hour
- Staging deployment: 30 minutes
- Testing & validation: 1 hour
- Production deployment: 1 hour
**Total: 7-9 hours**

### Realistic (Some debugging required)
- Frontend test fixes: 3-4 hours
- Coverage increase: 3-4 hours
- Infrastructure setup: 1 hour
- E2E fixes: 2 hours
- Staging deployment: 1 hour
- Testing & validation: 2 hours
- Production deployment: 1 hour
**Total: 13-15 hours**

### Pessimistic (Major issues found)
- Frontend test fixes: 8-16 hours
- Infrastructure setup: 3 hours
- Staging deployment: 2 hours
- Testing & validation: 4 hours
- Production deployment: 2 hours
**Total: 19-27 hours**

## Success Criteria

### MVP Launch Criteria
1. All tests passing (backend & frontend)
2. 70%+ test coverage on both ends
3. Successful staging deployment
4. E2E tests passing on staging
5. Performance benchmarks met
6. Security scan passed

### Post-Launch Monitoring
1. Zero critical errors in first 24 hours
2. API response time <500ms p95
3. Frontend load time <3s
4. User registration success rate >95%
5. Quest creation success rate >98%

## Next Steps After MVP

### Immediate (Week 1)
1. Monitor system stability
2. Gather user feedback
3. Fix any critical bugs
4. Performance optimization

### Short-term (Month 1)
1. Complete QuestFilters integration
2. Implement advanced search
3. Add notification system
4. Enhance mobile experience

### Long-term (Quarter 1)
1. EIP-712 signature implementation
2. Advanced reputation algorithms
3. Gamification features
4. API v2 planning

## Contact & Escalation

### Development Team
- Frontend Lead: [Contact]
- Backend Lead: [Contact]
- DevOps Lead: [Contact]

### Escalation Path
1. Development Lead
2. Engineering Manager
3. CTO

## Appendix

### Useful Commands
```bash
# Check test status
npm test

# View coverage report
npm run coverage

# Check AWS resources
aws cloudformation describe-stacks --stack-name civicforge-backend-dev

# View logs
aws logs tail /aws/lambda/civicforge-dev-createQuest --follow

# Database queries
aws dynamodb scan --table-name civicforge-quests-dev
```

### Environment URLs
- **Development**: http://localhost:3000
- **Staging**: https://staging.civicforge.com
- **Production**: https://app.civicforge.com

### Documentation Links
- [Architecture](./docs/reference/architecture.md)
- [API Reference](./docs/reference/api-reference.md)
- [Testing Guide](./docs/TESTING.md)
- [Security Model](./docs/reference/security-model.md)