# CivicForge AWS Deployment Checklist

## Pre-Deployment Requirements

### 1. AWS SSM Parameters (CRITICAL - Must be created before deployment)
Before deploying, create these SSM parameters in your target AWS account/region:
- [ ] `/civicforge/{stage}/cognito-user-pool-id` - Your Cognito User Pool ID
- [ ] `/civicforge/{stage}/cognito-app-client-id` - Your Cognito App Client ID
- [ ] `/civicforge/{stage}/frontend-url` - Frontend URL (optional, defaults to http://localhost:5173)

### 2. AWS Account Setup
- [ ] AWS CLI configured with appropriate credentials
- [ ] Serverless Framework installed (`npm install -g serverless`)
- [ ] Python 3.9 runtime available
- [ ] Docker installed (for serverless-python-requirements plugin)

### 3. CloudWatch Alarms Configuration
**CRITICAL**: Add SNS topic for alarm notifications:
```yaml
# Add this to resources section in serverless.yml:
AlarmNotificationsTopic:
  Type: AWS::SNS::Topic
  Properties:
    TopicName: ${self:service}-${self:provider.stage}-alarms
    Subscription:
      - Endpoint: your-email@example.com
        Protocol: email
```

Then update all CloudWatch alarms to include:
```yaml
AlarmActions:
  - !Ref AlarmNotificationsTopic
```

### 4. Lambda Function Optimization
Update Lambda function configurations for production:
```yaml
api:
  handler: handlers.api.handler
  memorySize: 512  # Increase from default 128MB
  timeout: 30      # Increase from default 3 seconds

createQuest:
  handler: handlers.create_quest.handler
  memorySize: 256
  timeout: 15

attestQuest:
  handler: handlers.attest_quest.handler
  memorySize: 256
  timeout: 15

deleteQuest:
  handler: handlers.delete_quest.handler
  memorySize: 256
  timeout: 15
```

## Deployment Steps

### 1. Install Dependencies
```bash
cd backend
npm install
pip install -r requirements.txt
```

### 2. Run Tests
```bash
python -m pytest
# Expected: 201 passed, ~21 integration test failures (expected without real AWS resources)
# Coverage: 72.68% (exceeds 70% requirement)
```

### 3. Deploy to Development
```bash
serverless deploy --stage dev --region us-east-1
```

### 4. Deploy to Production
```bash
serverless deploy --stage prod --region us-east-1
```

## Post-Deployment Verification

### 1. Verify Resources Created
- [ ] DynamoDB tables: users, quests, failed-rewards
- [ ] Lambda functions: api, createQuest, attestQuest, deleteQuest, createUserTrigger, reprocessFailedRewards
- [ ] API Gateway with JWT authorizer
- [ ] CloudWatch log groups and alarms
- [ ] SQS Dead Letter Queue for user creation

### 2. Test Endpoints
- [ ] Health check: `GET /health` (should return 200)
- [ ] Authenticated endpoints require valid JWT token

### 3. Monitor CloudWatch
- [ ] Check Lambda function logs
- [ ] Verify no immediate errors
- [ ] Confirm alarms are in OK state

## Security Considerations

### 1. Rate Limiting
- Implemented with slowapi
- Known issue: Forged JWTs can exhaust rate limits for legitimate users
- TODO: Implement rate limiting after authentication

### 2. IAM Permissions
- Fine-grained permissions per Lambda function
- DynamoDB attribute-level restrictions
- Principle of least privilege applied

### 3. Data Protection
- Point-in-time recovery enabled on all DynamoDB tables
- Dead letter queues for failed operations
- Input sanitization for XSS prevention

## Known Issues

### 1. Test Failures
- 21 integration tests fail locally (expected - they require real AWS resources)
- These tests will pass in deployed environment

### 2. Rate Limiter Vulnerability
- Medium severity: Attackers can forge JWTs to trigger rate limits for other users
- Mitigation: Future enhancement to integrate rate limiting post-authentication

## Monitoring & Maintenance

### 1. CloudWatch Alarms Monitor
- API errors and duration
- Lambda throttles and concurrent executions
- DLQ message age and count
- Failed reward processing

### 2. Regular Tasks
- Review CloudWatch logs weekly
- Check DLQ for stuck messages
- Monitor API error rates
- Review security logs for anomalies

## Rollback Plan

If issues occur:
```bash
# Rollback to previous version
serverless rollback --timestamp <timestamp>

# Or redeploy specific version
serverless deploy --stage <stage> --package <package-path>
```

## Contact & Support

- Architecture issues: Review HANDOVER.md
- Security concerns: See SECURITY_AUDIT_REPORT.md
- Lambda issues: Check CloudWatch logs first