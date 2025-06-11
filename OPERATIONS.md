# Operations Guide

## Environments

- **dev**: Development environment for testing
- **staging**: Pre-production environment
- **prod**: Production environment (auto-deployed from main branch)

## Deployment

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

### Alerts

Critical alerts configured for:
- Lambda error rate > 1%
- API Gateway 5xx errors > 10/minute
- DynamoDB throttling

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
1. Disable API Gateway: `aws apigateway update-rest-api --rest-api-id XXX --patch-operations op=replace,path=/policy,value=''`
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