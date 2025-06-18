# CivicForge Deployment Runbook

*Last Updated: January 2025*

## Overview

This runbook provides step-by-step instructions for deploying CivicForge to AWS environments. Always refer to [PROJECT_STATUS.md](../PROJECT_STATUS.md) for current deployment readiness status.

## Pre-Deployment Checklist

### Security Verification ✅
- [✓] API authentication configured (Cognito JWT authorizer)
- [✓] No hardcoded secrets or API keys
- [✓] IAM roles follow least privilege
- [✓] CORS properly configured
- [ ] Security scan passed (npm audit, pip-audit)
- [ ] No sensitive data in logs

### Code Quality ✅
- [✓] All tests passing
  - Backend: 85.78% coverage (269 tests) ✅
  - Frontend: 71.17% coverage (96 tests) ✅
  - Critical attestation flow tested ✅
- [ ] No linting errors
- [ ] TypeScript compilation successful

### Git Status
- [ ] All changes committed
- [ ] Working on correct branch
  - `main` for production (⚠️ currently on `testing-infrastructure`)
  - `staging` for staging
  - `develop` for development
- [ ] All PRs merged
- [ ] Release tagged (production only)

### Environment Configuration
- [✓] SSM parameters configured for target environment
  - Cognito User Pool ID
  - Cognito App Client ID
  - Frontend URL
- [ ] Environment variables documented
- [ ] Feature flags configured

## Deployment Environments

### Development
- **Purpose**: Active development and testing
- **URL**: https://dev.civicforge.example.com
- **AWS Account**: Development
- **Deployment**: Automatic on push to `develop`

### Staging
- **Purpose**: Pre-production testing
- **URL**: https://staging.civicforge.com
- **AWS Account**: Production (separate stage)
- **Deployment**: Manual trigger
- **Status**: ✅ Fully configured with Cognito and SSM parameters

### Production
- **Purpose**: Live environment
- **URL**: https://civicforge.example.com
- **AWS Account**: Production
- **Deployment**: Manual with approvals
- **Protection**: Canary deployments, automated rollback

## Standard Deployment Process

### 1. Pre-Deployment Validation

```bash
# Run all checks
npm run check:deployment

# This runs:
# - All tests
# - Linting
# - TypeScript compilation
# - Security audits
# - Build verification
```

### 2. Deploy Backend

```bash
cd backend

# Deploy to target environment
npm run deploy:$ENVIRONMENT

# For production, use canary deployment
npm run deploy:prod:canary
```

### 3. Deploy Frontend

```bash
cd frontend

# Build for target environment
npm run build:$ENVIRONMENT

# Deploy to S3
aws s3 sync dist/ s3://civicforge-frontend-$ENVIRONMENT/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"
```

### 4. Post-Deployment Verification

```bash
# Health check
curl https://$ENVIRONMENT.civicforge.example.com/api/v1/health

# Run smoke tests
npm run test:smoke:$ENVIRONMENT

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=civicforge-api-$ENVIRONMENT-api \
  --statistics Sum \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300
```

## Canary Deployment (Production Only)

### 1. Deploy Canary Version

```bash
# Deploy with 10% traffic split
./scripts/deploy-canary.sh production 10

# Monitor for 30 minutes
./scripts/monitor-canary.sh production
```

### 2. Monitor Metrics

Watch for:
- Error rate < 1%
- P95 latency < 1s
- No anomalous patterns

### 3. Promote or Rollback

```bash
# If metrics are good, promote to 100%
./scripts/promote-canary.sh production

# If issues detected, rollback immediately
./scripts/rollback.sh production
```

## Feature Flag Deployment

For risky changes, use feature flags instead of canary:

```bash
# Deploy with feature disabled
aws appconfig update-configuration-profile \
  --application-id civicforge \
  --configuration-profile-id feature-flags \
  --content '{
    "flags": {
      "new_feature": {
        "enabled": false
      }
    }
  }'

# Deploy code
npm run deploy:prod

# Enable for 10% of users
aws appconfig update-configuration-profile \
  --application-id civicforge \
  --configuration-profile-id feature-flags \
  --content '{
    "flags": {
      "new_feature": {
        "enabled": true,
        "rollout_percentage": 10
      }
    }
  }'
```

## Rollback Procedures

### Immediate Rollback (< 5 min)

```bash
# One-command rollback
./scripts/rollback.sh $ENVIRONMENT

# This script:
# 1. Reverts Lambda to previous version
# 2. Restores previous frontend from S3
# 3. Invalidates CloudFront
# 4. Sends alert to team
```

### Manual Rollback Steps

If automated rollback fails:

```bash
# 1. Rollback Lambda functions
FUNCTIONS=(api createQuest attestQuest deleteQuest)
for func in "${FUNCTIONS[@]}"; do
  aws lambda update-alias \
    --function-name civicforge-$ENVIRONMENT-$func \
    --name live \
    --function-version $PREVIOUS_VERSION
done

# 2. Rollback frontend (requires S3 versioning)
aws s3api list-object-versions \
  --bucket civicforge-frontend-$ENVIRONMENT \
  --prefix index.html \
  --max-items 2 \
  --query 'Versions[1].VersionId' \
  --output text | xargs -I {} \
  aws s3api copy-object \
    --bucket civicforge-frontend-$ENVIRONMENT \
    --copy-source civicforge-frontend-$ENVIRONMENT/index.html?versionId={} \
    --key index.html

# 3. Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"
```

## Staging Environment Setup

✅ **Staging environment is already configured!**

The following SSM parameters have been set:
- `/civicforge/staging/cognito-user-pool-id`: us-east-1_wKpnasV5v
- `/civicforge/staging/cognito-app-client-id`: 71uqkredjv9aj4icaa2crlvvp3
- `/civicforge/staging/frontend-url`: https://staging.civicforge.com

For future reference or other environments, use the setup script:
```bash
./scripts/setup-cognito.sh [environment]
```

## Emergency Procedures

### Complete Service Outage

1. **Immediate Actions**:
   ```bash
   # Enable maintenance mode
   aws appconfig update-configuration-profile \
     --application-id civicforge \
     --configuration-profile-id feature-flags \
     --content '{"flags": {"maintenance_mode": {"enabled": true}}}'
   ```

2. **Rollback to last known good**:
   ```bash
   ./scripts/emergency-rollback.sh production
   ```

3. **Notify stakeholders**:
   ```bash
   ./scripts/send-incident-alert.sh P1 "Complete service outage"
   ```

### Data Corruption

1. **Stop writes**:
   ```bash
   # Disable write endpoints via feature flag
   aws appconfig update-configuration-profile \
     --application-id civicforge \
     --configuration-profile-id feature-flags \
     --content '{"flags": {"read_only_mode": {"enabled": true}}}'
   ```

2. **Restore from backup**:
   ```bash
   # DynamoDB point-in-time recovery
   aws dynamodb restore-table-to-point-in-time \
     --source-table-name civicforge-quests-prod \
     --target-table-name civicforge-quests-prod-restored \
     --restore-date-time "2024-01-15T12:00:00Z"
   ```

## Monitoring During Deployment

### Key Metrics to Watch

1. **Error Rates**:
   ```bash
   watch -n 5 'aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Errors \
     --dimensions Name=FunctionName,Value=civicforge-api-prod-api \
     --statistics Sum \
     --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60'
   ```

2. **Response Times**:
   ```bash
   aws logs insights query \
     --log-group-name /aws/lambda/civicforge-api-prod-api \
     --start-time $(date -u -d "10 minutes ago" +%s) \
     --end-time $(date +%s) \
     --query 'fields @timestamp, duration | stats avg(duration) by bin(1m)'
   ```

3. **Active Users**:
   - Monitor CloudFront requests
   - Check Cognito authentication rates

## Post-Deployment Tasks

### 1. Verify Core Functionality

```bash
# Run E2E tests against deployed environment
npm run test:e2e:$ENVIRONMENT

# Manual verification checklist:
# - [ ] Can create account
# - [ ] Can login
# - [ ] Can create quest
# - [ ] Can claim quest
# - [ ] Can submit work
# - [ ] Can attest completion
```

### 2. Update Documentation

- [ ] Update deployment log
- [ ] Note any issues encountered
- [ ] Update runbook if procedures changed

### 3. Team Communication

```bash
# Send deployment notification
./scripts/notify-deployment.sh $ENVIRONMENT $VERSION
```

## Troubleshooting

### Common Issues

#### Frontend not updating after deployment
- CloudFront cache not invalidated
- Browser cache holding old version
- S3 sync failed partway through

**Solution**:
```bash
# Force cache clear
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"

# Verify S3 content
aws s3 ls s3://civicforge-frontend-$ENVIRONMENT/ --recursive | head
```

#### Lambda cold starts after deployment
- Normal behavior for first invocations
- Can cause timeouts on complex operations

**Solution**:
```bash
# Warm up functions
for i in {1..5}; do
  curl https://$ENVIRONMENT.civicforge.example.com/api/v1/health &
done
wait
```

#### Database migrations failed
- Schema mismatch between code and database
- Failed DynamoDB table updates

**Solution**:
- Check CloudFormation stack for errors
- Manually apply missing attributes
- Restore from backup if corrupted

## Contact Information

### Escalation Path

1. **On-Call Engineer**: Check PagerDuty rotation
2. **Team Lead**: [Name] - [Phone]
3. **AWS Support**: [Support Case URL]
4. **Security Team**: security@civicforge.example.com

### Key Resources

- [AWS Console](https://console.aws.amazon.com)
- [CloudWatch Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=CivicForge)
- [Deployment Logs](https://github.com/civicforge/civicforge/deployments)
- [Incident History](./incidents/)

---

Remember: When in doubt, rollback first and investigate later. User experience is paramount.