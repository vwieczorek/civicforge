# Operations Guide

This guide covers deployment procedures, infrastructure management, monitoring, and troubleshooting for CivicForge.

## Table of Contents

1. [Environments](#environments)
2. [Infrastructure Overview](#infrastructure-overview)
3. [Deployment Procedures](#deployment-procedures)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Troubleshooting](#troubleshooting)
6. [Rollback Procedures](#rollback-procedures)
7. [Security Considerations](#security-considerations)

## Environments

| Environment | Purpose | Branch | URL |
|------------|---------|---------|-----|
| **dev** | Development testing | Any | https://dev-api.civicforge.example.com |
| **staging** | Pre-production validation | Any (clean) | https://staging-api.civicforge.example.com |
| **prod** | Production | main only | https://api.civicforge.example.com |

## Infrastructure Overview

### Architecture Components

**Frontend Infrastructure:**
- Private S3 bucket with CloudFront distribution
- Origin Access Control (OAC) for secure access
- Automatic cache invalidation on deployments
- HTTPS enforced with SPA routing support

**Backend Infrastructure:**
- Modular Lambda functions with isolated IAM roles
- API Gateway with throttling (100 rps, 200 burst)
- DynamoDB tables with Point-in-Time Recovery
- SSM Parameter Store for configuration
- Dead Letter Queue for failed operations

**Security Features:**
- OIDC-based GitHub Actions (no long-lived credentials)
- Per-function IAM roles (least privilege)
- Input sanitization with Pydantic/bleach
- JWT authentication via AWS Cognito

## Deployment Procedures

### Prerequisites

1. **Environment Setup**
   ```bash
   # Configure AWS CLI
   aws configure
   
   # Verify Node.js 18+ and Python 3.11+
   node --version
   python --version
   ```

2. **Required SSM Parameters**
   ```bash
   # Set for each environment
   aws ssm put-parameter --name "/civicforge/{stage}/cognito-user-pool-id" --value "YOUR_VALUE" --type SecureString
   aws ssm put-parameter --name "/civicforge/{stage}/cognito-app-client-id" --value "YOUR_VALUE" --type SecureString
   aws ssm put-parameter --name "/civicforge/{stage}/frontend-url" --value "YOUR_VALUE" --type String
   ```

### Deployment Commands

#### Development Deployment
```bash
# Flexible deployment for testing
./scripts/deploy.sh dev
```

#### Staging Deployment
```bash
# Pre-flight checks
git status  # Must be clean
npm test    # All tests must pass

# Deploy
./scripts/deploy.sh staging

# Validate
curl https://staging-api.civicforge.example.com/health
npm run test:e2e -- --env=staging
```

#### Production Deployment
```bash
# Pre-flight checks
git checkout main
git pull origin main
./scripts/check-mvp-readiness.sh  # Must pass all checks

# Deploy with confirmation
./scripts/deploy.sh prod

# Monitor logs during deployment
aws logs tail /aws/lambda/civicforge-api-prod-api --follow
```

### Pre-Deployment Checklist

#### Code Quality
- [ ] All tests passing (`npm test`)
- [ ] Backend coverage ≥70% (currently 85.78% ✅)
- [ ] Frontend coverage ≥70% (currently 71.17% ✅)
- [ ] No linting errors or warnings
- [ ] TypeScript compilation successful

#### Security Review
- [ ] No hardcoded secrets or API keys
- [ ] All API endpoints authenticated
- [ ] CORS properly configured (no wildcards)
- [ ] Input validation on all endpoints
- [ ] XSS protection via bleach sanitization

#### Git Status
- [ ] All changes committed
- [ ] Working on correct branch (main for prod)
- [ ] All feature branches merged
- [ ] No merge conflicts
- [ ] Release tagged appropriately

#### Infrastructure Configuration
- [ ] All SSM parameters set for target stage
- [ ] IAM roles follow least-privilege
- [ ] CloudWatch alarms configured
- [ ] DynamoDB backup enabled

### Post-Deployment Verification

1. **API Health Checks**
   ```bash
   # Check health endpoint
   curl https://api.civicforge.example.com/health
   
   # Test authentication
   curl -X POST https://api.civicforge.example.com/api/v1/test-auth \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. **Frontend Verification**
   - Load the application
   - Test login/logout flow
   - Create a test quest
   - Complete dual-attestation flow
   - Verify user profile data
   - Check quest list displays

3. **Monitor CloudWatch Dashboard**
   - Check error rates < 1%
   - Verify latency p99 < 1000ms
   - Confirm no DLQ messages
   - Verify all alarms active

4. **Database Verification**
   - Tables created successfully
   - Indexes active and queryable
   - Point-in-time recovery enabled
   - No throttling occurring

## Monitoring & Alerts

### CloudWatch Alarms

| Alarm | Threshold | Action |
|-------|-----------|--------|
| API Error Rate | > 1% for 5 min | Page on-call |
| Failed Rewards | > 0 abandoned | Email notification |
| API Latency | p99 > 1000ms | Email notification |
| DynamoDB Throttles | > 0 | Auto-scale + notify |
| Lambda Errors | > 10 in 5 min | Page on-call |

### Key Metrics to Monitor

- **API Gateway**: Request count, 4XX/5XX rates, latency
- **Lambda**: Invocations, errors, duration, concurrent executions
- **DynamoDB**: Consumed capacity, throttles, user errors
- **Failed Rewards**: DLQ depth, reprocessing success rate

### Log Analysis

```bash
# View recent API logs
aws logs tail /aws/lambda/civicforge-api-{stage}-api --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/civicforge-api-prod-api \
  --filter-pattern "ERROR"

# View specific request
aws logs filter-log-events \
  --log-group-name /aws/lambda/civicforge-api-prod-api \
  --filter-pattern "{$.requestId = 'REQUEST_ID'}"
```

## Troubleshooting

### Common Issues

#### 1. Cold Start Latency
**Symptoms**: First request after idle period is slow (3-5s)
**Solution**: 
- Enable provisioned concurrency for critical functions
- Implement API Gateway caching for read operations

#### 2. DynamoDB Throttling
**Symptoms**: ProvisionedThroughputExceededException errors
**Solution**:
- Tables use on-demand billing (auto-scales)
- If persistent, check for hot partition keys
- Review access patterns for optimization

#### 3. Authentication Failures
**Symptoms**: 401 errors on valid tokens
**Solution**:
```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id YOUR_POOL_ID

# Check token expiry settings
# Ensure frontend refreshes tokens before expiry
```

#### 4. Failed Reward Distribution
**Symptoms**: Rewards not distributed after quest completion
**Solution**:
```bash
# Check DLQ for failed messages
aws sqs get-queue-attributes \
  --queue-url YOUR_DLQ_URL \
  --attribute-names ApproximateNumberOfMessages

# Manually trigger reprocessor
aws lambda invoke \
  --function-name civicforge-reprocess-failed-rewards-prod \
  --payload '{}' \
  response.json
```

### Debug Commands

```bash
# Get Lambda function configuration
aws lambda get-function --function-name civicforge-api-prod-api

# List recent invocations
aws logs describe-log-streams \
  --log-group-name /aws/lambda/civicforge-api-prod-api \
  --order-by LastEventTime \
  --descending

# Check DynamoDB table status
aws dynamodb describe-table --table-name civicforge-quests-prod
```

## Feature Flag Management

CivicForge uses AWS AppConfig for runtime feature control without deployments.

### Configuration

Feature flags are managed through AWS AppConfig with:
- Instant updates without code deployment
- Percentage-based rollouts
- User targeting capabilities
- A/B testing support

### Usage

```python
# Backend: Check feature flag
from src.feature_flags_v2 import FeatureFlagService

flags = FeatureFlagService()
if flags.is_enabled('new_attestation_flow', user_id):
    # Use new implementation
```

```typescript
// Frontend: React hook
const { isEnabled } = useFeatureFlags();
if (isEnabled('new_attestation_flow')) {
  // Show new UI
}
```

### Common Flags

- `wallet_signature_required`: Enforce EIP-712 signatures
- `new_attestation_flow`: Enhanced attestation UI
- `maintenance_mode`: Disable write operations

## Canary Deployments

### Process

1. **Deploy new version**
   ```bash
   ./scripts/deploy-canary.sh staging 10
   ```

2. **Monitor metrics** (15-30 minutes)
   - Error rates
   - Response times
   - Business metrics

3. **Promote or rollback**
   ```bash
   # Promote to 100%
   ./scripts/promote-canary.sh staging
   
   # Or rollback
   ./scripts/rollback.sh staging
   ```

### Health Checks

Automated rollback triggers on:
- Error rate > 5%
- P95 latency > 2s
- Failed health checks

## Rollback Procedures

### Immediate Rollback (< 5 minutes)

1. **Backend Rollback**
   ```bash
   cd backend
   
   # List recent deployments
   serverless deploy list --stage prod
   
   # Rollback to previous version
   serverless rollback --stage prod --timestamp TIMESTAMP
   ```

2. **Frontend Rollback**
   ```bash
   # Revert to previous git tag
   git checkout tags/v1.2.3
   
   # Rebuild and deploy
   cd frontend
   npm run build
   aws s3 sync dist/ s3://civicforge-frontend-prod/
   
   # Invalidate CloudFront cache
   aws cloudfront create-invalidation \
     --distribution-id YOUR_DIST_ID \
     --paths "/*"
   ```

### Database Recovery

- DynamoDB Point-in-Time Recovery enabled
- Can restore to any point in last 35 days
- Failed rewards table maintains audit history

```bash
# Create table restore
aws dynamodb restore-table-to-point-in-time \
  --source-table-name civicforge-quests-prod \
  --target-table-name civicforge-quests-prod-restored \
  --restore-date-time "2024-01-15T12:00:00Z"
```

## Security Considerations

### Access Control

1. **AWS IAM**
   - Developers: Read-only access to logs and metrics
   - DevOps: Deploy permissions for staging
   - Admin: Full access for production changes

2. **API Security**
   - Rate limiting: 100 requests/second per IP
   - JWT validation on all protected endpoints
   - Request signing for admin operations

### Secrets Management

All secrets stored in SSM Parameter Store:
```bash
# List all parameters
aws ssm describe-parameters --filters "Key=Name,Values=/civicforge/"

# Update a secret
aws ssm put-parameter \
  --name "/civicforge/prod/api-key" \
  --value "NEW_VALUE" \
  --type SecureString \
  --overwrite
```

### Security Checklist

- [ ] Rotate Cognito signing keys quarterly
- [ ] Review IAM policies monthly
- [ ] Audit CloudTrail logs for unusual activity
- [ ] Update dependencies for security patches
- [ ] Perform penetration testing annually

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 | Service down | < 15 min | API returning 500s, database unavailable |
| P2 | Degraded service | < 1 hour | High latency, partial failures |
| P3 | Minor issue | < 4 hours | UI glitch, non-critical feature broken |
| P4 | Low priority | Next business day | Documentation updates, minor improvements |

### Response Procedures

1. **Acknowledge** incident in monitoring system
2. **Assess** impact and severity
3. **Communicate** status to stakeholders
4. **Mitigate** immediate issues
5. **Resolve** root cause
6. **Document** post-mortem

### Emergency Contacts

- On-Call Engineer: [Rotation Schedule]
- AWS Support: [Case URL]
- Security Team: security@civicforge.example.com

---

For deployment checklist and validation steps, see [Pre-Deployment Checklist](#deployment-procedures).
For architecture details, see [ARCHITECTURE.md](../ARCHITECTURE.md).