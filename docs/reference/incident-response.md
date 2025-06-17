# Incident Response Guide

*Last Updated: January 2025*

## Overview

This guide provides step-by-step procedures for responding to production incidents in CivicForge. Follow these procedures to minimize downtime, protect user data, and restore service quickly.

## Incident Severity Levels

### P1 - Critical (Complete Outage)
- **Definition**: Service is completely unavailable or data integrity is compromised
- **Response Time**: Immediate (< 15 minutes)
- **Examples**:
  - API Gateway returns 5xx errors for all requests
  - Database corruption or data loss
  - Authentication service down
  - Security breach detected

### P2 - Major (Partial Outage)
- **Definition**: Core functionality degraded but service partially available
- **Response Time**: < 1 hour
- **Examples**:
  - Quest creation failing but other features work
  - Significant performance degradation (> 5s response times)
  - Payment processing errors
  - High error rate (> 10%) on specific endpoints

### P3 - Minor (Feature Degradation)
- **Definition**: Non-critical features affected
- **Response Time**: < 4 hours
- **Examples**:
  - Search functionality slow
  - Email notifications delayed
  - Non-critical Lambda function errors
  - UI glitches affecting < 5% of users

### P4 - Low (Cosmetic Issues)
- **Definition**: Minor issues with no functional impact
- **Response Time**: Next business day
- **Examples**:
  - Styling issues
  - Typos in UI
  - Non-blocking console errors

## Initial Response Procedures

### 1. Assess the Situation (First 5 minutes)

```bash
# Check service health
curl https://api.civicforge.com/health

# Check CloudWatch dashboard
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=civicforge-api-prod-api \
  --statistics Sum \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300

# Check recent alarm history
aws cloudwatch describe-alarm-history \
  --alarm-name civicforge-prod-api-errors \
  --max-records 10
```

### 2. Notify Stakeholders

#### P1 Incidents
1. Page on-call engineer immediately
2. Create incident channel in Slack: `#incident-YYYY-MM-DD-description`
3. Send initial notification:
   ```
   🚨 P1 INCIDENT DECLARED
   
   **Issue**: [Brief description]
   **Impact**: [User impact]
   **Status**: Investigating
   **Lead**: @[your-name]
   
   Updates every 15 minutes.
   ```

#### P2-P3 Incidents
1. Post in #civicforge-alerts channel
2. Tag relevant team members
3. Create incident ticket

### 3. Enable Maintenance Mode (If Required)

For complete outages, enable maintenance mode to show users a friendly error:

```bash
# Enable maintenance mode
aws appconfig update-configuration-profile \
  --application-id civicforge \
  --configuration-profile-id feature-flags \
  --content '{
    "flags": {
      "maintenance_mode": {
        "enabled": true,
        "message": "CivicForge is undergoing maintenance. We'll be back shortly."
      }
    }
  }'

# Deploy the configuration
aws appconfig start-deployment \
  --application-id civicforge \
  --environment-id prod \
  --deployment-strategy-id immediate \
  --configuration-profile-id feature-flags \
  --configuration-version $VERSION
```

## Diagnosis Procedures

### Lambda Function Errors

1. **Check function logs**:
```bash
# View recent logs
aws logs tail /aws/lambda/civicforge-prod-api --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/civicforge-prod-api \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

2. **Check function metrics**:
```bash
# Get error count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=civicforge-prod-api \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300

# Get throttles
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=civicforge-prod-api \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300
```

### Database Issues

1. **Check DynamoDB metrics**:
```bash
# Check for throttled requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=civicforge-quests-prod \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300

# Check consumed capacity
aws dynamodb describe-table --table-name civicforge-quests-prod \
  --query 'Table.ConsumedCapacity'
```

2. **Verify table status**:
```bash
aws dynamodb describe-table --table-name civicforge-quests-prod \
  --query 'Table.TableStatus'
```

### Authentication Issues

1. **Check Cognito status**:
```bash
# Describe user pool
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-1_xxxxx \
  --query 'UserPool.Status'

# Check recent auth events
aws cognito-idp admin-list-user-auth-events \
  --user-pool-id us-east-1_xxxxx \
  --username test@example.com \
  --max-items 10
```

### API Gateway Issues

1. **Check API Gateway metrics**:
```bash
# 4XX errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value=civicforge-api \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300

# 5XX errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=civicforge-api \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300
```

## Common Issues and Solutions

### Issue: Lambda Cold Start Timeouts

**Symptoms**: Intermittent timeouts, especially after deployments

**Solution**:
```bash
# Increase reserved concurrency
aws lambda put-function-concurrency \
  --function-name civicforge-prod-api \
  --reserved-concurrent-executions 5

# Or increase timeout
aws lambda update-function-configuration \
  --function-name civicforge-prod-api \
  --timeout 30
```

### Issue: DynamoDB Throttling

**Symptoms**: ProvisionedThroughputExceededException errors

**Solution**:
```bash
# Switch to on-demand billing (immediate fix)
aws dynamodb update-table \
  --table-name civicforge-quests-prod \
  --billing-mode PAY_PER_REQUEST
```

### Issue: High Error Rate After Deployment

**Symptoms**: Spike in errors immediately after deployment

**Solution**:
```bash
# Rollback to previous version
cd backend
serverless rollback --stage prod

# Or rollback specific function
aws lambda update-alias \
  --function-name civicforge-prod-api \
  --name live \
  --function-version $PREVIOUS_VERSION
```

### Issue: Authentication Failures

**Symptoms**: 401 errors, users can't log in

**Solution**:
1. Check Cognito quotas aren't exceeded
2. Verify app client settings haven't changed
3. Check for expired certificates
4. Verify CORS configuration

## Recovery Procedures

### Quick Rollback (< 5 minutes)

For issues caused by recent deployment:

```bash
# One-command rollback
./scripts/rollback.sh prod

# Verify rollback
curl https://api.civicforge.com/health
```

### Database Recovery

If data corruption is detected:

```bash
# Stop writes immediately
aws appconfig update-configuration-profile \
  --application-id civicforge \
  --configuration-profile-id feature-flags \
  --content '{"flags": {"read_only_mode": {"enabled": true}}}'

# Restore from point-in-time backup
aws dynamodb restore-table-to-point-in-time \
  --source-table-name civicforge-quests-prod \
  --target-table-name civicforge-quests-prod-recovered \
  --restore-date-time "2024-01-15T12:00:00Z"

# Verify data integrity
aws dynamodb scan \
  --table-name civicforge-quests-prod-recovered \
  --max-items 10
```

### Frontend Recovery

For frontend issues:

```bash
# List recent S3 versions
aws s3api list-object-versions \
  --bucket civicforge-frontend-prod \
  --prefix index.html \
  --max-items 5

# Restore previous version
aws s3api copy-object \
  --bucket civicforge-frontend-prod \
  --copy-source civicforge-frontend-prod/index.html?versionId=XXXXX \
  --key index.html

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"
```

## Post-Incident Procedures

### 1. Verify Resolution

```bash
# Run smoke tests
npm run test:smoke:prod

# Check metrics are normal
./scripts/check-health.sh prod

# Verify user reports have stopped
```

### 2. Disable Maintenance Mode

```bash
aws appconfig update-configuration-profile \
  --application-id civicforge \
  --configuration-profile-id feature-flags \
  --content '{"flags": {"maintenance_mode": {"enabled": false}}}'
```

### 3. Document the Incident

Create an incident report with:
- Timeline of events
- Root cause analysis
- Impact assessment
- Actions taken
- Lessons learned
- Follow-up items

Template:
```markdown
# Incident Report: [Title]

**Date**: 2024-01-15
**Severity**: P1
**Duration**: 45 minutes
**Lead**: @engineer

## Timeline
- 14:00 - First alert received
- 14:05 - Incident declared
- 14:15 - Root cause identified
- 14:30 - Fix deployed
- 14:45 - Service restored

## Root Cause
[Detailed explanation]

## Impact
- Users affected: ~1,000
- Requests failed: ~5,000
- Revenue impact: $0

## Resolution
[Steps taken to resolve]

## Follow-up Actions
- [ ] Add monitoring for X
- [ ] Update runbook for Y
- [ ] Schedule blameless postmortem
```

### 4. Conduct Postmortem (Within 48 hours)

- Schedule blameless postmortem meeting
- Invite all stakeholders
- Focus on system improvements, not blame
- Create action items with owners and deadlines

## Escalation Paths

### On-Call Rotation
Primary: Check PagerDuty schedule
Secondary: Check #oncall-schedule in Slack

### Management Escalation
1. Engineering Manager: [Name] - [Phone]
2. VP of Engineering: [Name] - [Phone]
3. CTO: [Name] - [Phone]

### External Support
- AWS Support: [Case URL]
- Cognito Support: [Contact]
- CloudFlare Support: [Contact]

## Monitoring Links

- [CloudWatch Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=CivicForge-Prod)
- [Lambda Functions](https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions)
- [DynamoDB Tables](https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables)
- [API Gateway](https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis)
- [Cognito User Pool](https://console.aws.amazon.com/cognito/users/?region=us-east-1)

## Useful Commands Reference

```bash
# Check all service health
./scripts/health-check.sh prod

# View real-time logs
./scripts/tail-logs.sh prod

# Run diagnostics
./scripts/diagnose.sh prod

# Emergency rollback
./scripts/emergency-rollback.sh prod
```

## Prevention Checklist

To prevent incidents:
- [ ] Always run tests before deployment
- [ ] Deploy to staging first
- [ ] Monitor metrics after deployment
- [ ] Have rollback plan ready
- [ ] Keep runbooks updated
- [ ] Regular disaster recovery drills
- [ ] Review and update alerts monthly

---

Remember: Stay calm, communicate clearly, and focus on restoring service. Every incident is a learning opportunity.