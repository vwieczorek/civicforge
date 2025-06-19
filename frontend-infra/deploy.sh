#!/bin/bash
# Deploy frontend infrastructure for CivicForge

# Set default stage to dev if not provided
STAGE=${1:-dev}

echo "Deploying frontend infrastructure for stage: $STAGE"

# Navigate to the frontend-infra directory
cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing serverless dependencies..."
    npm install
fi

# Deploy the infrastructure
echo "Deploying CloudFront and S3 infrastructure..."
npx serverless deploy --stage $STAGE --region us-east-1

# Get the outputs
echo ""
echo "Deployment complete! Getting stack outputs..."
aws cloudformation describe-stacks \
    --stack-name civicforge-frontend-infra-$STAGE \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "Frontend infrastructure deployed successfully!"
echo ""
echo "Important: The S3 bucket and CloudFront distribution are now ready."
echo "The GitHub Actions workflow will handle deploying the frontend assets."