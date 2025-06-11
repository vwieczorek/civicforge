# Operations Guide

## Environments

- **dev**: Development environment for testing
- **staging**: Pre-production environment
- **prod**: Production environment (auto-deployed from main branch)

## Infrastructure Setup Status

### ✅ Completed Infrastructure Components

**Secure Frontend Hosting:**
- Private S3 bucket with CloudFront distribution
- Origin Access Control (OAC) implemented  
- Cache invalidation on deployments
- HTTPS enforced with SPA routing support

**Backend Infrastructure:**
- Serverless AWS Lambda with API Gateway
- DynamoDB with atomic operations and Point-in-Time Recovery
- Environment variable management with SSM
- PostConfirmation Lambda trigger for user onboarding
- Dead Letter Queues for failed operations

**Security & Deployment:**
- OIDC-based CI/CD (secure, no long-lived keys)
- GitHub Actions workflow with environment-specific deployments
- CloudWatch alarms for critical failures
- XSS protection with bleach sanitization

## MVP Pre-Launch Validation

### Production Readiness Tasks

**High Priority:**
- Backend test coverage: 55% → 70% 
- Frontend test coverage: 7% → 40%
- Fix failing integration tests

**Medium Priority:**
- Security audit (pip-audit, npm audit)
- Enhanced monitoring dashboards

Note: API Gateway rate limiting is already configured in serverless.yml (100 req/s, 200 burst)

### Deployment Status

🚧 **DEVELOPMENT READY, PRODUCTION PENDING** - Core architecture complete, critical tasks remaining:

**✅ Infrastructure Foundation:**
- Frontend runtime errors fixed
- DynamoDB Point-in-Time Recovery enabled  
- OIDC security implemented (run `./scripts/setup-oidc.sh`)
- Secure infrastructure with atomic operations
- Centralized authorization logic
- XSS protection implemented with bleach
- User onboarding with PostConfirmation trigger
- CloudWatch alarms for critical failures

**🚧 Critical Tasks for Production:**
- Backend test coverage: 55% → 70% (pytest.ini requirement)
- Frontend test coverage: 7% → 40% minimum
- Fix failing integration tests

## Deployment

### Prerequisites
1. AWS CLI configured: `aws configure`
2. Node.js 18+ and Python 3.11+
3. Infrastructure setup completed (OIDC, CloudFront)

### Infrastructure Setup (First Time Only)
```bash
# 1. Set up frontend infrastructure (CloudFront + S3)
npm run setup:infra:staging  # or :prod

# 2. Create Cognito resources
npm run setup:cognito

# 3. Note the output IDs and create frontend/.env
cp frontend/.env.example frontend/.env
# Edit with your Cognito IDs
```

### Deploy to Development
```bash
npm run deploy:dev
```

### Deploy to Production
Production deployments happen automatically when PRs are merged to `main`.

Manual deployment (emergency only):
```bash
npm run deploy:prod
```

### First Production Deployment
```bash
# 1. Deploy with feature flags OFF
npm run deploy:prod

# 2. Smoke test core functionality
npm run test:smoke

# 3. Enable feature flags for internal team
aws ssm put-parameter --name /civicforge/prod/feature-rewards --value "internal"

# 4. Monitor for 24 hours, then gradual rollout
# 10% -> 50% -> 100% with monitoring between each stage
```

### CI/CD Security Setup ✅ COMPLETE
**Status: OIDC authentication configured**

```bash
# One command to set up secure OIDC deployment
./scripts/setup-oidc.sh
```

This replaces insecure long-lived IAM keys with secure OIDC:
1. ✅ Creates IAM OIDC provider for GitHub 
2. ✅ Creates IAM roles with least-privilege permissions per environment
3. ✅ Updates GitHub Actions workflow for OIDC authentication
4. 🎯 **Action Required:** Follow script output to configure GitHub environment secrets

**Manual steps after running script:**
1. GitHub Repo Settings > Environments > Create: development, staging, production
2. Add `AWS_ROLE_TO_ASSUME` secret to each environment (script provides exact ARNs)
3. Delete old `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` repository secrets
4. Test deployment by pushing to any branch

## Configuration

### Environment Variables

Required for all environments:
- `COGNITO_REGION`: AWS region (e.g., us-east-1)
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_APP_CLIENT_ID`: Cognito App Client ID
- `USERS_TABLE`: DynamoDB users table name
- `QUESTS_TABLE`: DynamoDB quests table name

### Secrets Management

Secrets are stored in AWS Systems Manager Parameter Store:
- `/civicforge/dev/*`
- `/civicforge/prod/*`

Access via serverless.yml:
```yaml
environment:
  API_KEY: ${ssm:/civicforge/${self:provider.stage}/api-key}
```

## Monitoring

### CloudWatch Logs

Lambda logs are in CloudWatch Log Groups:
- `/aws/lambda/civicforge-dev-api`
- `/aws/lambda/civicforge-prod-api`

### Key Metrics

Monitor in CloudWatch Dashboard:
- Lambda invocations
- Lambda errors
- Lambda duration
- DynamoDB consumed capacity
- API Gateway 4xx/5xx errors

**Business Metrics (Custom):**
- `quests_created` - New quests per hour
- `attestations_submitted` - Attestation rate
- `quests_completed` - Successful completions
- `failed_rewards` - Failed reward distributions
- `concurrent_attestation_conflicts` - Race condition occurrences

### Alerts

Critical alerts configured for:
- Lambda error rate > 1%
- User creation DLQ depth > 0 (already implemented)
- API errors > 5 per 5 minutes (needs implementation)

**API Error Monitoring ✅ CONFIGURED**
CloudWatch alarms are configured for:
- Lambda error rate > 1%
- User creation DLQ depth > 0
- API Gateway 5xx errors
- API Gateway 5xx errors > 10/minute
- DynamoDB throttling
- `failed_rewards` count increases by >1 (P1)
- Error rate >5% for 5 minutes (P1)
- API p95 latency >1s (P2)

## Emergency Procedures

### Rollback

```bash
# List recent deployments
serverless deploy list --stage prod

# Rollback to timestamp
serverless rollback --timestamp 1639619904 --stage prod
```

### Direct Database Access

**Use only in emergencies:**

```bash
# Connect to DynamoDB
aws dynamodb scan --table-name civicforge-prod-quests

# Update specific item
aws dynamodb update-item \
  --table-name civicforge-prod-quests \
  --key '{"questId": {"S": "quest-id"}}' \
  --update-expression "SET #s = :status" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":status": {"S": "OPEN"}}'
```

### Circuit Breaker

If system is compromised:
1. Disable API Gateway: `aws apigateway update-rest-api --rest-api-id ${API_ID} --patch-operations op=replace,path=/policy,value=''`
2. Investigate CloudWatch logs
3. Fix issue
4. Re-enable API

## Backup & Recovery

DynamoDB Point-in-Time Recovery is enabled:
- 35-day recovery window
- Restore via AWS Console or CLI

## Cost Management

Monitor via AWS Cost Explorer:
- Budget alert at $25/month
- Main costs: Lambda invocations, DynamoDB, CloudWatch Logs

Optimize by:
- Adjusting Lambda memory/timeout
- Implementing DynamoDB auto-scaling
- Setting CloudWatch log retention