#!/bin/bash
# Script to rotate Cognito credentials after potential exposure

set -e

echo "=== Cognito Credential Rotation Script ==="
echo "This script will help you rotate the exposed Cognito credentials"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Get current AWS identity
echo "Current AWS Identity:"
aws sts get-caller-identity

echo ""
read -p "Continue with credential rotation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rotation cancelled."
    exit 0
fi

# Set variables
STAGE=${1:-dev}
REGION=${2:-us-east-1}
echo ""
echo "Stage: $STAGE"
echo "Region: $REGION"

# Get the exposed credentials that need rotation
echo ""
echo "The following credentials were potentially exposed:"
echo "- User Pool ID: us-east-1_wKpnasV5v"
echo "- App Client ID: 71uqkredjv9aj4icaa2crlvvp3"

# Step 1: Create new app client
echo ""
echo "Step 1: Creating new app client..."
read -p "Enter the User Pool ID to update: " USER_POOL_ID

NEW_CLIENT=$(aws cognito-idp create-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-name "civicforge-web-client-rotated-$(date +%Y%m%d)" \
    --generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --prevent-user-existence-errors ENABLED \
    --enable-token-revocation \
    --region "$REGION" \
    --output json)

NEW_CLIENT_ID=$(echo "$NEW_CLIENT" | jq -r '.UserPoolClient.ClientId')
echo "New App Client ID created: $NEW_CLIENT_ID"

# Step 2: Update SSM parameters
echo ""
echo "Step 2: Updating SSM parameters..."
aws ssm put-parameter \
    --name "/civicforge/$STAGE/cognito-app-client-id" \
    --value "$NEW_CLIENT_ID" \
    --type "SecureString" \
    --overwrite \
    --region "$REGION"

echo "SSM parameter updated successfully"

# Step 3: Delete old app client
echo ""
echo "Step 3: Deleting old app client..."
read -p "Delete the old app client? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    aws cognito-idp delete-user-pool-client \
        --user-pool-id "$USER_POOL_ID" \
        --client-id "71uqkredjv9aj4icaa2crlvvp3" \
        --region "$REGION" || echo "Failed to delete old client (may already be deleted)"
fi

# Step 4: Create new frontend environment file
echo ""
echo "Step 4: Creating new frontend environment configuration..."
cat > frontend/.env.local << EOF
# Frontend Environment Variables
# Created: $(date)
# Note: Use .env.local for local development

# AWS Cognito Configuration
VITE_USER_POOL_ID=$USER_POOL_ID
VITE_USER_POOL_CLIENT_ID=$NEW_CLIENT_ID
VITE_AWS_REGION=$REGION

# API Configuration
VITE_API_URL=http://localhost:3001

# Feature Flags
VITE_ENABLE_MSW=true
EOF

echo "Created frontend/.env.local with new credentials"

# Step 5: Provide deployment instructions
echo ""
echo "=== Next Steps ==="
echo "1. Redeploy the backend to use the new client ID:"
echo "   cd backend && serverless deploy --stage $STAGE"
echo ""
echo "2. Update any frontend deployments with the new credentials"
echo ""
echo "3. Monitor CloudWatch logs for any authentication failures"
echo ""
echo "4. Consider enabling AWS CloudTrail for Cognito API calls"
echo ""
echo "=== Rotation Complete ==="
echo "Old Client ID: 71uqkredjv9aj4icaa2crlvvp3 (should be deleted)"
echo "New Client ID: $NEW_CLIENT_ID"
echo ""
echo "Remember to update all environments that use these credentials!"