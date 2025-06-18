#!/bin/bash

# Simplified setup script for AWS Cognito User Pool for CivicForge staging
set -e

STAGE=staging
REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="civicforge"

echo "🔐 Setting up Cognito for CivicForge ($STAGE environment)"

# Create User Pool with simpler command
USER_POOL_NAME="${PROJECT_NAME}-${STAGE}-user-pool"
echo "Creating User Pool: $USER_POOL_NAME"

# Create user pool with basic configuration
USER_POOL_RESPONSE=$(aws cognito-idp create-user-pool \
  --pool-name "$USER_POOL_NAME" \
  --region "$REGION" \
  --auto-verified-attributes email \
  --username-attributes email)

USER_POOL_ID=$(echo "$USER_POOL_RESPONSE" | jq -r '.UserPool.Id')
echo "✅ User Pool created: $USER_POOL_ID"

# Create App Client
APP_CLIENT_NAME="${PROJECT_NAME}-${STAGE}-app-client"
echo "Creating App Client: $APP_CLIENT_NAME"

APP_CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-name "$APP_CLIENT_NAME" \
  --region "$REGION")

APP_CLIENT_ID=$(echo "$APP_CLIENT_RESPONSE" | jq -r '.UserPoolClient.ClientId')
echo "✅ App Client created: $APP_CLIENT_ID"

# Store in SSM Parameter Store
echo "Storing configuration in SSM Parameter Store..."

aws ssm put-parameter \
  --name "/${PROJECT_NAME}/${STAGE}/cognito-user-pool-id" \
  --value "$USER_POOL_ID" \
  --type "String" \
  --overwrite \
  --region "$REGION"

aws ssm put-parameter \
  --name "/${PROJECT_NAME}/${STAGE}/cognito-app-client-id" \
  --value "$APP_CLIENT_ID" \
  --type "String" \
  --overwrite \
  --region "$REGION"

# Set the frontend URL for staging
FRONTEND_URL="https://staging.civicforge.com"

aws ssm put-parameter \
  --name "/${PROJECT_NAME}/${STAGE}/frontend-url" \
  --value "$FRONTEND_URL" \
  --type "String" \
  --overwrite \
  --region "$REGION"

echo "✅ Configuration stored in SSM"

# Output configuration
echo ""
echo "📋 Cognito Configuration:"
echo "User Pool ID: $USER_POOL_ID"
echo "App Client ID: $APP_CLIENT_ID"
echo "Region: $REGION"
echo "Stage: $STAGE"
echo ""
echo "✅ SSM Parameters configured:"
echo "  - /${PROJECT_NAME}/${STAGE}/cognito-user-pool-id"
echo "  - /${PROJECT_NAME}/${STAGE}/cognito-app-client-id"
echo "  - /${PROJECT_NAME}/${STAGE}/frontend-url"