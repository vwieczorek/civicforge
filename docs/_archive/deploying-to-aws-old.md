# How to Deploy CivicForge to AWS

This guide walks through deploying the CivicForge application to AWS.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js 18+ and Python 3.11+
- Serverless Framework installed: `npm install -g serverless`
- GitHub repository with OIDC configured

## Environment Setup

### 1. AWS SSM Parameters

Set the following parameters in AWS Systems Manager:

```bash
# Cognito configuration
aws ssm put-parameter --name "/civicforge/dev/cognito-user-pool-id" --value "YOUR_POOL_ID" --type String
aws ssm put-parameter --name "/civicforge/dev/cognito-app-client-id" --value "YOUR_CLIENT_ID" --type String

# Frontend URL (for CORS)
aws ssm put-parameter --name "/civicforge/dev/frontend-url" --value "https://your-domain.com" --type String
```

### 2. Environment Variables

Create `.env` files:

**Backend (.env)**
```bash
STAGE=dev
AWS_REGION=us-east-1
```

**Frontend (.env)**
```bash
VITE_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com
VITE_COGNITO_USER_POOL_ID=YOUR_POOL_ID
VITE_COGNITO_CLIENT_ID=YOUR_CLIENT_ID
```

## Deployment Steps

### 1. Deploy Backend

```bash
cd backend

# Install dependencies
npm install
pip install -r requirements.txt

# Deploy to AWS
serverless deploy --stage dev

# For production
serverless deploy --stage prod
```

The deployment will:
- Create Lambda functions with individual IAM roles
- Set up API Gateway with throttling
- Create DynamoDB tables with backup enabled
- Configure CloudWatch alarms
- Set up the failed rewards reprocessor

### 2. Deploy Frontend

```bash
cd frontend

# Build the application
npm run build

# Deploy to S3 and CloudFront
cd ../frontend-infra
serverless deploy --stage dev

# Upload built files to S3
aws s3 sync ../frontend/dist s3://civicforge-frontend-dev --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

## Post-Deployment Verification

### 1. Backend Health Check
```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-13T12:00:00Z"
}
```

### 2. Frontend Access
Navigate to your CloudFront URL and verify:
- Login page loads
- Can create account
- API calls succeed

### 3. Monitor CloudWatch
Check CloudWatch for:
- Lambda function logs
- API Gateway access logs
- Any alarms triggered

## Security Considerations

### IAM Roles
Each Lambda function has restricted permissions:
- `createQuest`: Can only deduct questCreationPoints
- `attestQuest`: Can only update XP, reputation, rewards
- `deleteQuest`: Only function with delete permissions

### API Security
- All endpoints require Cognito authentication
- CORS configured for specific domain
- API Gateway throttling prevents abuse

### Data Protection
- DynamoDB point-in-time recovery enabled
- Failed operations tracked in separate table
- All data encrypted at rest

## Rollback Procedure

If issues occur:

```bash
# List recent deployments
serverless deploy list --stage dev

# Rollback to previous version
serverless rollback --timestamp TIMESTAMP --stage dev
```

## Monitoring and Alerts

### CloudWatch Alarms
Configured alerts for:
- API error rate >5%
- Lambda function errors
- DynamoDB throttling
- Failed reward processing

### Logs
View logs:
```bash
# API Gateway logs
serverless logs -f api --stage dev

# Specific function logs
serverless logs -f createQuest --stage dev --tail
```

## Cost Optimization

- Lambda functions sized appropriately (128-256MB)
- DynamoDB on-demand billing
- CloudFront caching reduces S3 requests
- Scheduled functions run every 15 minutes (adjust if needed)

## Troubleshooting

### CORS Issues
- Verify frontend URL in SSM parameters
- Check API Gateway CORS configuration
- Ensure Authorization header is allowed

### Authentication Failures
- Verify Cognito configuration
- Check JWKS URL accessibility
- Ensure Lambda has internet access

### Performance Issues
- Check Lambda cold start times
- Monitor DynamoDB consumed capacity
- Review CloudWatch X-Ray traces