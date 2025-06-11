#!/bin/bash

# Deploy script for CivicForge
set -e

STAGE=${1:-dev}

echo "🚀 Deploying CivicForge to $STAGE environment"

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Deploy backend
echo "📦 Deploying backend..."
cd backend
npm install
serverless deploy --stage $STAGE

# Get API Gateway URL
API_URL=$(serverless info --stage $STAGE --verbose | grep "ServiceEndpoint:" | awk '{print $2}')
echo "✅ Backend deployed to: $API_URL"

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
    aws cloudfront create-invalidation \
        --distribution-id $DISTRIBUTION_ID \
        --paths "/*" \
        --output text
    
    echo "✅ Frontend deployed to: $FRONTEND_URL"
    
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