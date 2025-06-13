#!/bin/bash

# Deploy script for CivicForge with safety checks
set -e

STAGE=${1:-dev}

echo "🚀 Deploying CivicForge to $STAGE environment"

# Safety check: Ensure we're not on a feature branch for production
if [ "$STAGE" = "prod" ]; then
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo "❌ ERROR: Production deployments must be from 'main' branch"
        echo "   Current branch: $CURRENT_BRANCH"
        echo "   Please merge to main first."
        exit 1
    fi
fi

# Safety check: Ensure clean git status
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ ERROR: Uncommitted changes detected"
    echo "   Please commit or stash your changes before deploying"
    git status --short
    exit 1
fi

# Safety check: Run tests before deployment
echo "🧪 Running tests before deployment..."
npm test
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Tests failed. Fix failing tests before deploying."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Confirmation for production deployments
if [ "$STAGE" = "prod" ]; then
    echo ""
    echo "⚠️  WARNING: You are about to deploy to PRODUCTION"
    echo "   This will affect real users!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no) " -n 3 -r
    echo
    if [[ ! $REPLY =~ ^yes$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# Deploy backend
echo "📦 Deploying backend..."
cd backend
npm install

# Validate serverless configuration
echo "✓ Validating serverless configuration..."
serverless print --stage $STAGE > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Invalid serverless configuration"
    exit 1
fi

# Deploy with rollback capability
serverless deploy --stage $STAGE

# Get API Gateway URL
API_URL=$(serverless info --stage $STAGE --verbose | grep "ServiceEndpoint:" | awk '{print $2}')
echo "✅ Backend deployed to: $API_URL"

# Test the deployed API
echo "🧪 Testing deployed API health endpoint..."
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$HEALTH_CHECK" != "200" ]; then
    echo "❌ ERROR: Health check failed (HTTP $HEALTH_CHECK)"
    echo "   API may not be functioning correctly"
    echo "   Consider rolling back: serverless rollback --stage $STAGE"
    exit 1
fi
echo "✅ API health check passed"

# Deploy frontend (only for staging/prod)
if [ "$STAGE" != "dev" ]; then
    echo "📦 Deploying frontend..."
    
    # First, ensure frontend infrastructure is deployed
    echo "📦 Ensuring frontend infrastructure is up to date..."
    cd frontend-infra
    npm install
    serverless deploy --stage $STAGE
    
    # Get infrastructure outputs
    BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "civicforge-frontend-infra-$STAGE" \
        --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
        --output text)
    
    DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
        --stack-name "civicforge-frontend-infra-$STAGE" \
        --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
        --output text)
    
    FRONTEND_URL=$(aws cloudformation describe-stacks \
        --stack-name "civicforge-frontend-infra-$STAGE" \
        --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
        --output text)
    
    cd ../frontend
    
    # Get configuration from SSM
    export VITE_USER_POOL_ID=$(aws ssm get-parameter --name "/civicforge/$STAGE/cognito-user-pool-id" --query 'Parameter.Value' --output text)
    export VITE_USER_POOL_CLIENT_ID=$(aws ssm get-parameter --name "/civicforge/$STAGE/cognito-app-client-id" --query 'Parameter.Value' --output text)
    export VITE_AWS_REGION=${AWS_REGION:-us-east-1}
    export VITE_API_URL=$API_URL
    
    npm install
    npm run build
    
    # Deploy to private S3 bucket
    echo "📦 Syncing assets to S3..."
    aws s3 sync dist/ s3://$BUCKET_NAME/ --delete
    
    # Invalidate CloudFront cache
    echo "🔄 Invalidating CloudFront cache..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id $DISTRIBUTION_ID \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
    
    echo "✅ Frontend deployed to: $FRONTEND_URL"
    echo "   CloudFront invalidation ID: $INVALIDATION_ID"
    
    cd ..
else
    echo "ℹ️  Skipping frontend deployment for dev stage (use 'npm run dev' locally)"
fi

echo ""
echo "🎉 Deployment complete!"
echo "Stage: $STAGE"
echo "API URL: $API_URL"
[ "$STAGE" != "dev" ] && echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "Next steps:"
echo "1. Test the API: curl $API_URL/health"
[ "$STAGE" != "dev" ] && echo "2. Visit frontend: $FRONTEND_URL"
echo ""
echo "📋 Rollback instructions (if needed):"
echo "   Backend:  cd backend && serverless rollback --stage $STAGE"
[ "$STAGE" != "dev" ] && echo "   Frontend: Check CloudFormation console for previous versions"