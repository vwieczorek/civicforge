#!/bin/bash

# Fix pydantic deployment issues for Lambda
# Usage: ./scripts/fix_pydantic_deployment.sh [option1|option2]

set -e

echo "🔧 CivicForge Pydantic Lambda Fix Script"
echo "========================================"

OPTION=${1:-"1"}
STAGE=${2:-"staging"}

cd backend

if [ "$OPTION" = "1" ]; then
    echo "📦 Option 1: Using enhanced Docker build configuration"
    echo "This uses the exact Lambda runtime environment for building dependencies"
    
    # Clean previous builds
    echo "🧹 Cleaning previous builds..."
    rm -rf .serverless
    
    # Ensure Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    echo "🚀 Deploying with enhanced configuration..."
    npx serverless deploy --stage $STAGE --region us-east-1
    
elif [ "$OPTION" = "2" ]; then
    echo "📦 Option 2: Downgrading to Pydantic v1"
    echo "This uses the older, more compatible version of Pydantic"
    
    # Backup current requirements
    cp requirements.txt requirements.txt.backup
    
    # Downgrade pydantic
    echo "📝 Updating requirements.txt..."
    sed -i.bak 's/pydantic==2.5.3/pydantic==1.10.13/' requirements.txt
    sed -i.bak 's/pydantic-settings==2.1.0/# pydantic-settings not needed for v1/' requirements.txt
    
    # Clean and deploy
    echo "🧹 Cleaning previous builds..."
    rm -rf .serverless
    
    echo "🚀 Deploying with Pydantic v1..."
    npx serverless deploy --stage $STAGE --region us-east-1
    
    echo ""
    echo "💡 Note: You may need to update some code for Pydantic v1 compatibility"
    echo "   Check the migration guide: https://docs.pydantic.dev/latest/migration/"
    
else
    echo "❌ Invalid option. Usage: $0 [1|2] [stage]"
    echo "   Option 1: Enhanced Docker build (recommended)"
    echo "   Option 2: Downgrade to Pydantic v1"
    exit 1
fi

# Test the deployment
echo ""
echo "🧪 Testing deployment..."
API_URL=$(npx serverless info --stage $STAGE --verbose | grep "endpoint:" | head -1 | awk '{print $2}')

if [ -z "$API_URL" ]; then
    echo "❌ Could not determine API URL"
else
    echo "📍 API URL: $API_URL"
    echo "🏥 Testing health endpoint..."
    
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
    
    if [ "$HEALTH_STATUS" = "200" ]; then
        echo "✅ Health check passed! API is working correctly."
        echo ""
        echo "🎉 Deployment successful!"
        echo "   API Endpoint: $API_URL"
        echo "   Stage: $STAGE"
    else
        echo "❌ Health check failed (HTTP $HEALTH_STATUS)"
        echo "   Check CloudWatch logs: /aws/lambda/civicforge-api-$STAGE-api"
        echo ""
        echo "Fetching recent logs..."
        aws logs tail /aws/lambda/civicforge-api-$STAGE-api --since 5m | tail -20
    fi
fi