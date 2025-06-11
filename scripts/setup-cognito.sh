#!/bin/bash

# Setup script for AWS Cognito User Pool for CivicForge
# This script creates and configures the Cognito resources needed for the MVP

set -e

STAGE=${1:-dev}
REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="civicforge"

echo "🔐 Setting up Cognito for CivicForge ($STAGE environment)"

# Create User Pool
USER_POOL_NAME="${PROJECT_NAME}-${STAGE}-user-pool"
echo "Creating User Pool: $USER_POOL_NAME"

USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name "$USER_POOL_NAME" \
  --region "$REGION" \
  --auto-verified-attributes email \
  --username-attributes email \
  --password-policy "MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false" \
  --user-attribute-update-settings "AttributesRequireVerificationBeforeUpdate=email" \
  --schema \
    "Name=email,AttributeDataType=String,Required=true,Mutable=true" \
    "Name=name,AttributeDataType=String,Required=false,Mutable=true" \
    "Name=custom:ethereum_address,AttributeDataType=String,Mutable=true,DeveloperOnlyAttribute=false" \
  --query 'UserPool.Id' \
  --output text)

echo "✅ User Pool created: $USER_POOL_ID"

# Create App Client
APP_CLIENT_NAME="${PROJECT_NAME}-${STAGE}-app-client"
echo "Creating App Client: $APP_CLIENT_NAME"

APP_CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-name "$APP_CLIENT_NAME" \
  --region "$REGION" \
  --generate-secret false \
  --refresh-token-validity 30 \
  --access-token-validity 60 \
  --id-token-validity 60 \
  --token-validity-units "AccessToken=minutes,IdToken=minutes,RefreshToken=days" \
  --read-attributes "email" "name" "custom:ethereum_address" \
  --write-attributes "email" "name" "custom:ethereum_address" \
  --explicit-auth-flows "ALLOW_REFRESH_TOKEN_AUTH" "ALLOW_USER_SRP_AUTH" \
  --prevent-user-existence-errors ENABLED \
  --query 'UserPoolClient.ClientId' \
  --output text)

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

# Get the frontend URL from environment or use default
FRONTEND_URL=${FRONTEND_URL:-"http://localhost:5173"}
if [ "$STAGE" == "prod" ]; then
  FRONTEND_URL="https://civicforge.com"
elif [ "$STAGE" == "staging" ]; then
  FRONTEND_URL="https://staging.civicforge.com"
fi

aws ssm put-parameter \
  --name "/${PROJECT_NAME}/${STAGE}/frontend-url" \
  --value "$FRONTEND_URL" \
  --type "String" \
  --overwrite \
  --region "$REGION"

echo "✅ Configuration stored in SSM"

# Output configuration for frontend
echo ""
echo "📋 Frontend Configuration (add to frontend/.env):"
echo "VITE_AWS_REGION=$REGION"
echo "VITE_USER_POOL_ID=$USER_POOL_ID"
echo "VITE_USER_POOL_CLIENT_ID=$APP_CLIENT_ID"

# Output summary
echo ""
echo "🎉 Cognito setup complete!"
echo "User Pool ID: $USER_POOL_ID"
echo "App Client ID: $APP_CLIENT_ID"
echo "Region: $REGION"
echo "Stage: $STAGE"
echo ""
echo "Next steps:"
echo "1. Update frontend/.env with the configuration above"
echo "2. Run 'npm run deploy:$STAGE' to deploy the backend"
echo "3. Run 'npm run dev' in frontend/ to test locally"