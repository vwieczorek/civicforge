# CivicForge Production Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [AWS Account Setup](#aws-account-setup)
4. [Cognito Configuration](#cognito-configuration)
5. [SSM Parameters Setup](#ssm-parameters-setup)
6. [Local Development Environment](#local-development-environment)
7. [CI/CD Pipeline Setup](#cicd-pipeline-setup)
8. [Manual Deployment Process](#manual-deployment-process)
9. [Post-Deployment Verification](#post-deployment-verification)
10. [Monitoring and Alerting](#monitoring-and-alerting)
11. [Cost Management](#cost-management)
12. [Troubleshooting](#troubleshooting)
13. [Rollback Procedures](#rollback-procedures)
14. [Security Checklist](#security-checklist)
15. [Operational Runbook](#operational-runbook)

## Overview

This guide provides comprehensive, step-by-step instructions for deploying the CivicForge serverless application to AWS. It covers everything from initial AWS setup to production monitoring.

**Architecture Overview:**
- API Gateway (HTTP API) with Cognito JWT authorization
- Lambda functions (Python 3.9) for business logic
- DynamoDB tables for data persistence
- CloudWatch for logging and monitoring
- SQS Dead Letter Queue for failed operations
- X-Ray for distributed tracing

## Prerequisites

### Required Tools
```bash
# Check versions
aws --version          # AWS CLI v2.x required
node --version         # Node.js 14.x or later
npm --version          # NPM 6.x or later
python --version       # Python 3.9
docker --version       # Docker 20.x or later
serverless --version   # Serverless Framework 3.x

# Install if missing
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

npm install -g serverless
```

### AWS Account Requirements
- AWS account with billing enabled
- Administrative access or specific IAM permissions (see below)
- Ability to create resources in desired region (default: us-east-1)

## AWS Account Setup

### 1. Create Deployment IAM User

```bash
# Create IAM user for deployments
aws iam create-user --user-name civicforge-deployer

# Create access key
aws iam create-access-key --user-name civicforge-deployer > deployer-credentials.json

# Save the credentials securely!
cat deployer-credentials.json
```

### 2. Create and Attach Deployment Policy

Create file `deployment-policy.json`:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "s3:*",
                "lambda:*",
                "apigateway:*",
                "dynamodb:*",
                "iam:*",
                "logs:*",
                "cloudwatch:*",
                "sqs:*",
                "xray:*",
                "ssm:GetParameter",
                "ssm:PutParameter",
                "kms:Decrypt",
                "kms:CreateGrant",
                "cognito-idp:DescribeUserPool"
            ],
            "Resource": "*"
        }
    ]
}
```

```bash
# Create policy
aws iam create-policy \
    --policy-name CivicForgeDeploymentPolicy \
    --policy-document file://deployment-policy.json \
    --description "Policy for CivicForge serverless deployments"

# Attach policy to user (replace ACCOUNT_ID)
aws iam attach-user-policy \
    --user-name civicforge-deployer \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/CivicForgeDeploymentPolicy
```

### 3. Configure AWS CLI Profile

```bash
# Configure deployment profile
aws configure --profile civicforge-deploy
# Enter:
# - Access Key ID from deployer-credentials.json
# - Secret Access Key from deployer-credentials.json
# - Default region: us-east-1
# - Default output format: json

# Test configuration
aws sts get-caller-identity --profile civicforge-deploy
```

## Cognito Configuration

### 1. Create Cognito User Pool

```bash
# Create user pool configuration file
cat > cognito-user-pool.json << 'EOF'
{
    "PoolName": "civicforge-users",
    "Policies": {
        "PasswordPolicy": {
            "MinimumLength": 8,
            "RequireUppercase": true,
            "RequireLowercase": true,
            "RequireNumbers": true,
            "RequireSymbols": true
        }
    },
    "AutoVerifiedAttributes": ["email"],
    "UsernameAttributes": ["email"],
    "Schema": [
        {
            "Name": "email",
            "AttributeDataType": "String",
            "Required": true,
            "Mutable": true
        },
        {
            "Name": "name",
            "AttributeDataType": "String",
            "Required": false,
            "Mutable": true
        }
    ],
    "UserPoolAddOns": {
        "AdvancedSecurityMode": "ENFORCED"
    },
    "AccountRecoverySetting": {
        "RecoveryMechanisms": [
            {
                "Priority": 1,
                "Name": "verified_email"
            }
        ]
    }
}
EOF

# Create user pool
aws cognito-idp create-user-pool \
    --cli-input-json file://cognito-user-pool.json \
    --profile civicforge-deploy \
    --region us-east-1 > user-pool-output.json

# Extract User Pool ID
export USER_POOL_ID=$(cat user-pool-output.json | jq -r '.UserPool.Id')
echo "User Pool ID: $USER_POOL_ID"
```

### 2. Create App Client

```bash
# Create app client
aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name civicforge-web-client \
    --generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --prevent-user-existence-errors ENABLED \
    --enable-token-revocation \
    --profile civicforge-deploy \
    --region us-east-1 > app-client-output.json

# Extract App Client ID
export APP_CLIENT_ID=$(cat app-client-output.json | jq -r '.UserPoolClient.ClientId')
echo "App Client ID: $APP_CLIENT_ID"
```

### 3. Configure Lambda Trigger

```bash
# This will be done automatically by serverless.yml during deployment
# The Lambda permission is already configured in the template
```

## SSM Parameters Setup

### Critical Parameters (Required Before Deployment)

```bash
# Set the stage (dev, staging, or prod)
export STAGE=dev

# Store Cognito IDs in SSM
aws ssm put-parameter \
    --name "/civicforge/$STAGE/cognito-user-pool-id" \
    --value "$USER_POOL_ID" \
    --type "SecureString" \
    --description "Cognito User Pool ID for CivicForge $STAGE" \
    --profile civicforge-deploy \
    --region us-east-1

aws ssm put-parameter \
    --name "/civicforge/$STAGE/cognito-app-client-id" \
    --value "$APP_CLIENT_ID" \
    --type "SecureString" \
    --description "Cognito App Client ID for CivicForge $STAGE" \
    --profile civicforge-deploy \
    --region us-east-1

# Store frontend URL (optional, has default)
aws ssm put-parameter \
    --name "/civicforge/$STAGE/frontend-url" \
    --value "https://civicforge.example.com" \
    --type "String" \
    --description "Frontend URL for CivicForge $STAGE" \
    --profile civicforge-deploy \
    --region us-east-1
```

### Verify Parameters

```bash
# List all parameters
aws ssm describe-parameters \
    --parameter-filters "Key=Name,Values=/civicforge/$STAGE/" \
    --profile civicforge-deploy \
    --region us-east-1

# Get parameter values (for verification)
aws ssm get-parameter \
    --name "/civicforge/$STAGE/cognito-user-pool-id" \
    --with-decryption \
    --profile civicforge-deploy \
    --region us-east-1
```

## Local Development Environment

### 1. Clone and Setup Repository

```bash
# Clone repository
git clone https://github.com/yourorg/civicforge.git
cd civicforge/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install
```

### 2. Local Environment Configuration

```bash
# Create .env.local file
cat > .env.local << EOF
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_APP_CLIENT_ID=$APP_CLIENT_ID
COGNITO_REGION=us-east-1
USERS_TABLE=civicforge-dev-users
QUESTS_TABLE=civicforge-dev-quests
FAILED_REWARDS_TABLE=civicforge-dev-failed-rewards
LOG_LEVEL=DEBUG
FRONTEND_URL=http://localhost:5173
FF_REWARD_DISTRIBUTION=false
FF_SIGNATURE_ATTESTATION=true
FF_DISPUTE_RESOLUTION=false
EOF
```

### 3. Run Tests Locally

```bash
# Run all tests
python -m pytest -v

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run only unit tests (skip integration)
python -m pytest -m "not integration" -v

# Security scan
bandit -r src/

# Dependency audit
pip-audit
```

## CI/CD Pipeline Setup

### GitHub Actions Configuration

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy CivicForge

on:
  push:
    branches:
      - develop
      - main
  pull_request:
    branches:
      - main

env:
  AWS_DEFAULT_REGION: us-east-1
  NODE_VERSION: 18

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          cd backend
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest-cov
      
      - name: Run linting
        run: |
          cd backend
          # Add your linting commands
          python -m flake8 src/ --max-line-length=120
      
      - name: Run security scan
        run: |
          cd backend
          bandit -r src/
      
      - name: Run tests
        run: |
          cd backend
          python -m pytest -m "not integration" -v --cov=src
      
      - name: Check dependencies
        run: |
          cd backend
          pip-audit

  deploy-dev:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Install Serverless
        run: npm install -g serverless
      
      - name: Install dependencies
        run: |
          cd backend
          npm install
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_DEFAULT_REGION }}
      
      - name: Deploy to Dev
        run: |
          cd backend
          serverless deploy --stage dev --verbose
      
      - name: Run integration tests
        run: |
          cd backend
          python -m pytest -m "integration" -v
      
      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Dev deployment ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

  deploy-prod:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Install Serverless
        run: npm install -g serverless
      
      - name: Install dependencies
        run: |
          cd backend
          npm install
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID_PROD }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY_PROD }}
          aws-region: ${{ env.AWS_DEFAULT_REGION }}
      
      - name: Deploy to Production
        run: |
          cd backend
          serverless deploy --stage prod --verbose
      
      - name: Smoke Tests
        run: |
          cd backend
          # Add smoke test script
          python scripts/smoke_tests.py --stage prod
      
      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Production deployment ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Manual Deployment Process

### 1. Pre-Deployment Checklist

```bash
# Verify AWS credentials
aws sts get-caller-identity --profile civicforge-deploy

# Verify SSM parameters exist
aws ssm get-parameter --name "/civicforge/$STAGE/cognito-user-pool-id" --profile civicforge-deploy

# Run tests
cd backend
python -m pytest -v

# Package application
serverless package --stage $STAGE --profile civicforge-deploy
```

### 2. Deploy to Development

```bash
cd backend
export AWS_PROFILE=civicforge-deploy
export STAGE=dev

# First deployment
serverless deploy --stage $STAGE --verbose

# Subsequent deployments (faster)
serverless deploy --stage $STAGE --function api
```

### 3. Deploy to Production

```bash
cd backend
export AWS_PROFILE=civicforge-deploy-prod
export STAGE=prod

# Create deployment package
serverless package --stage $STAGE

# Review changes
serverless diff --stage $STAGE

# Deploy with confirmation
read -p "Deploy to production? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    serverless deploy --stage $STAGE --package .serverless --verbose
fi
```

## Post-Deployment Verification

### 1. Verify Resources

```bash
# List deployed functions
aws lambda list-functions \
    --query "Functions[?starts_with(FunctionName, 'civicforge-$STAGE')].[FunctionName, Runtime, LastModified]" \
    --output table \
    --profile civicforge-deploy

# Check DynamoDB tables
aws dynamodb list-tables \
    --query "TableNames[?starts_with(@, 'civicforge-$STAGE')]" \
    --profile civicforge-deploy

# Verify API Gateway
aws apigatewayv2 get-apis \
    --query "Items[?Name=='civicforge-api-$STAGE'].[ApiId, Name, ApiEndpoint]" \
    --output table \
    --profile civicforge-deploy
```

### 2. Health Check

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name civicforge-api-$STAGE \
    --query "Stacks[0].Outputs[?OutputKey=='HttpApiUrl'].OutputValue" \
    --output text \
    --profile civicforge-deploy)

echo "API Endpoint: $API_ENDPOINT"

# Test health endpoint
curl -X GET "$API_ENDPOINT/health"
# Expected: {"status": "healthy", "service": "civicforge-api", "stage": "dev"}
```

### 3. Test Authentication

```bash
# Create test user (if not exists)
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username testuser@example.com \
    --user-attributes Name=email,Value=testuser@example.com \
    --temporary-password "TempPass123!" \
    --profile civicforge-deploy

# Get auth token (requires additional scripting)
# See scripts/get_auth_token.py
```

## Monitoring and Alerting

### 1. Create SNS Topic for Alarms

```bash
# Create SNS topic
aws sns create-topic \
    --name civicforge-$STAGE-alarms \
    --profile civicforge-deploy \
    --region us-east-1

# Subscribe email
aws sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:civicforge-$STAGE-alarms \
    --protocol email \
    --notification-endpoint your-email@example.com \
    --profile civicforge-deploy
```

### 2. Update CloudWatch Alarms

After deployment, update all alarms to include the SNS topic:

```bash
# Script to update all alarms
TOPIC_ARN="arn:aws:sns:us-east-1:ACCOUNT_ID:civicforge-$STAGE-alarms"

# List all alarms
aws cloudwatch describe-alarms \
    --alarm-name-prefix "civicforge-api-$STAGE" \
    --query "MetricAlarms[].AlarmName" \
    --output text \
    --profile civicforge-deploy | \
while read alarm; do
    echo "Updating $alarm"
    aws cloudwatch put-metric-alarm \
        --alarm-name "$alarm" \
        --alarm-actions "$TOPIC_ARN" \
        --profile civicforge-deploy
done
```

### 3. Lambda Power Tuning

Deploy AWS Lambda Power Tuning for optimization:

```bash
# Deploy from Serverless Application Repository
aws serverlessrepo create-cloud-formation-template \
    --application-id arn:aws:serverlessrepo:us-east-1:451282441545:applications/aws-lambda-power-tuning \
    --semantic-version 4.3.0

# Deploy the stack
aws cloudformation deploy \
    --template-file packaged.yaml \
    --stack-name lambda-power-tuning \
    --capabilities CAPABILITY_IAM \
    --profile civicforge-deploy

# Run power tuning for each function
# See: https://github.com/alexcasalboni/aws-lambda-power-tuning
```

## Cost Management

### 1. Set up Budget Alerts

```bash
# Create budget
aws budgets create-budget \
    --account-id ACCOUNT_ID \
    --budget file://budget.json \
    --notifications-with-subscribers file://notifications.json \
    --profile civicforge-deploy
```

Create `budget.json`:
```json
{
    "BudgetName": "civicforge-monthly",
    "BudgetLimit": {
        "Amount": "100",
        "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
        "TagKeyValue": ["Key=project,Value=civicforge"]
    }
}
```

Create `notifications.json`:
```json
[
    {
        "Notification": {
            "NotificationType": "ACTUAL",
            "ComparisonOperator": "GREATER_THAN",
            "Threshold": 80,
            "ThresholdType": "PERCENTAGE"
        },
        "Subscribers": [
            {
                "SubscriptionType": "EMAIL",
                "Address": "alerts@example.com"
            }
        ]
    }
]
```

### 2. Enable Cost Anomaly Detection

```bash
aws ce create-anomaly-monitor \
    --anomaly-monitor '{
        "MonitorName": "civicforge-cost-monitor",
        "MonitorType": "CUSTOM",
        "MonitorDimension": "SERVICE",
        "MonitorSpecification": {
            "Tags": {
                "Key": "project",
                "Values": ["civicforge"]
            }
        }
    }' \
    --profile civicforge-deploy
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Deployment Fails with "Stack already exists"

```bash
# Delete the stack and redeploy
serverless remove --stage $STAGE --profile civicforge-deploy
serverless deploy --stage $STAGE --profile civicforge-deploy
```

#### 2. Lambda Function Timeouts

```bash
# Check function logs
serverless logs -f api -t --stage $STAGE

# Increase timeout in serverless.yml
# timeout: 30  # seconds
```

#### 3. DynamoDB Throttling

```bash
# Check table metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ConsumedReadCapacityUnits \
    --dimensions Name=TableName,Value=civicforge-$STAGE-quests \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-01T01:00:00Z \
    --period 300 \
    --statistics Sum \
    --profile civicforge-deploy
```

#### 4. Authentication Errors

```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool \
    --user-pool-id $USER_POOL_ID \
    --profile civicforge-deploy

# Check JWT configuration in API Gateway
aws apigatewayv2 get-authorizers \
    --api-id API_ID \
    --profile civicforge-deploy
```

### Viewing Logs

```bash
# Tail function logs
serverless logs -f api -t --stage $STAGE

# Search logs
aws logs filter-log-events \
    --log-group-name /aws/lambda/civicforge-$STAGE-api \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '1 hour ago' +%s)000 \
    --profile civicforge-deploy
```

### Checking Dead Letter Queue

```bash
# Get DLQ URL
DLQ_URL=$(aws sqs get-queue-url \
    --queue-name civicforge-api-$STAGE-user-creation-dlq \
    --query 'QueueUrl' \
    --output text \
    --profile civicforge-deploy)

# Check message count
aws sqs get-queue-attributes \
    --queue-url $DLQ_URL \
    --attribute-names ApproximateNumberOfMessages \
    --profile civicforge-deploy

# View messages (without deleting)
aws sqs receive-message \
    --queue-url $DLQ_URL \
    --max-number-of-messages 10 \
    --visibility-timeout 0 \
    --profile civicforge-deploy
```

## Rollback Procedures

### 1. Manual Rollback

```bash
# List previous deployments
serverless deploy list --stage $STAGE --profile civicforge-deploy

# Rollback to specific timestamp
serverless rollback --timestamp 1639077762 --stage $STAGE --profile civicforge-deploy
```

### 2. Automated Rollback Script

Create `scripts/auto_rollback.py`:
```python
#!/usr/bin/env python3
import boto3
import time
import subprocess
import sys

def check_health(api_endpoint):
    """Check if API is healthy"""
    # Implementation here
    pass

def get_error_rate(function_name, start_time):
    """Get Lambda error rate"""
    cloudwatch = boto3.client('cloudwatch')
    # Implementation here
    pass

def rollback(stage, timestamp):
    """Execute serverless rollback"""
    cmd = f"serverless rollback --timestamp {timestamp} --stage {stage}"
    subprocess.run(cmd, shell=True, check=True)

if __name__ == "__main__":
    # Monitor for 5 minutes after deployment
    # Rollback if error rate > 5% or health check fails
    pass
```

### 3. Emergency Procedures

```bash
# Disable API Gateway (stop all traffic)
aws apigatewayv2 update-stage \
    --api-id API_ID \
    --stage-name $STAGE \
    --throttle-settings '{"RateLimit": 0, "BurstLimit": 0}' \
    --profile civicforge-deploy

# Scale down Lambda concurrency (stop processing)
aws lambda put-function-concurrency \
    --function-name civicforge-$STAGE-api \
    --reserved-concurrent-executions 0 \
    --profile civicforge-deploy
```

## Security Checklist

### Pre-Deployment Security Checks

- [ ] All dependencies scanned with `pip-audit`
- [ ] Code scanned with `bandit`
- [ ] No hardcoded secrets in code
- [ ] All sensitive parameters in SSM SecureString
- [ ] IAM policies follow least privilege
- [ ] API endpoints have authentication (except /health)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (N/A - using DynamoDB)
- [ ] XSS prevention with input sanitization
- [ ] Rate limiting configured

### Post-Deployment Security Verification

```bash
# 1. Verify IAM policies are restrictive
aws iam get-role-policy \
    --role-name civicforge-api-$STAGE-api-role \
    --policy-name api-policy \
    --profile civicforge-deploy

# 2. Check API authentication
curl -X GET "$API_ENDPOINT/api/v1/quests" \
    -H "Authorization: Bearer invalid-token"
# Expected: 401 Unauthorized

# 3. Verify encrypted environment variables
aws lambda get-function-configuration \
    --function-name civicforge-$STAGE-api \
    --query 'Environment.Variables' \
    --profile civicforge-deploy

# 4. Check CloudTrail is enabled
aws cloudtrail describe-trails \
    --trail-name-list civicforge-trail \
    --profile civicforge-deploy
```

## Operational Runbook

### Daily Operations

1. **Check CloudWatch Dashboard**
   - Error rates < 1%
   - API latency P95 < 1 second
   - No alarms in ALARM state

2. **Review Logs**
   ```bash
   # Check for errors in last 24 hours
   ./scripts/daily_log_review.sh $STAGE
   ```

3. **Monitor DLQ**
   - Ensure no messages stuck > 1 hour
   - Investigate and reprocess failed messages

### Weekly Operations

1. **Cost Review**
   - Check AWS Cost Explorer
   - Verify no unexpected charges
   - Review Lambda invocation patterns

2. **Security Scan**
   ```bash
   # Run dependency updates
   cd backend
   pip-audit
   npm audit
   ```

3. **Performance Review**
   - Run Lambda Power Tuning on high-usage functions
   - Review X-Ray traces for bottlenecks

### Monthly Operations

1. **Capacity Planning**
   - Review DynamoDB usage patterns
   - Adjust Lambda reserved concurrency if needed
   - Update budget alerts

2. **Disaster Recovery Test**
   - Test backup restoration
   - Verify rollback procedures
   - Update runbook based on findings

### Incident Response

1. **High Error Rate**
   - Check CloudWatch Logs for error patterns
   - Review recent deployments
   - Consider rollback if errors persist

2. **Performance Degradation**
   - Check Lambda concurrent executions
   - Review DynamoDB throttling metrics
   - Scale up if necessary

3. **Security Incident**
   - Disable affected Lambda functions
   - Rotate compromised credentials
   - Review CloudTrail logs
   - Notify security team

## Appendix

### Useful Scripts

#### Get Authentication Token
Create `scripts/get_auth_token.py`:
```python
#!/usr/bin/env python3
import boto3
import json
import sys

def get_auth_token(username, password, user_pool_id, client_id):
    client = boto3.client('cognito-idp')
    
    response = client.initiate_auth(
        ClientId=client_id,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )
    
    return response['AuthenticationResult']['IdToken']

if __name__ == "__main__":
    # Usage: python get_auth_token.py username password
    token = get_auth_token(sys.argv[1], sys.argv[2], 
                          os.environ['USER_POOL_ID'], 
                          os.environ['APP_CLIENT_ID'])
    print(f"Authorization: Bearer {token}")
```

#### Smoke Tests
Create `scripts/smoke_tests.py`:
```python
#!/usr/bin/env python3
import requests
import sys
import os

def run_smoke_tests(api_endpoint, auth_token):
    tests = [
        ("GET", "/health", None, 200),
        ("GET", "/api/v1/quests", auth_token, 200),
        ("GET", "/api/v1/feature-flags", auth_token, 200),
    ]
    
    for method, path, token, expected_status in tests:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = requests.request(method, f"{api_endpoint}{path}", headers=headers)
        
        if response.status_code != expected_status:
            print(f"FAIL: {method} {path} returned {response.status_code}")
            sys.exit(1)
        else:
            print(f"PASS: {method} {path}")
    
    print("All smoke tests passed!")

if __name__ == "__main__":
    api_endpoint = sys.argv[1]
    auth_token = os.environ.get('AUTH_TOKEN', '')
    run_smoke_tests(api_endpoint, auth_token)
```

### References

- [Serverless Framework Documentation](https://www.serverless.com/framework/docs)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Lambda Power Tuning](https://github.com/alexcasalboni/aws-lambda-power-tuning)

---

This deployment guide is version controlled. Last updated: 2024-01-01
For updates or corrections, please submit a pull request.