#!/bin/bash

# Setup OIDC for GitHub Actions CI/CD
# This script sets up secure OIDC-based deployment instead of long-lived IAM keys

set -e

echo "🔐 Setting up OIDC for GitHub Actions CI/CD"
echo "=========================================="

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"

# Get repository information
REPO_NAME=$(basename "$(git remote get-url origin)" .git)
REPO_OWNER=$(git remote get-url origin | sed -n 's/.*github\.com[:/]\([^/]*\)\/.*/\1/p')
echo "✅ Repository: $REPO_OWNER/$REPO_NAME"

# Step 1: Create OIDC Identity Provider
echo ""
echo "📋 Step 1: Creating OIDC Identity Provider..."

# Check if OIDC provider already exists
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com" &>/dev/null; then
    echo "✅ OIDC Provider already exists"
else
    echo "Creating OIDC Identity Provider..."
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
    echo "✅ OIDC Provider created"
fi

# Step 2: Create IAM roles for each environment
create_deployment_role() {
    local STAGE=$1
    local BRANCH_PATTERN=$2
    local ROLE_NAME="civicforge-deploy-$STAGE"
    
    echo ""
    echo "📋 Creating IAM role for $STAGE environment..."
    
    # Create trust policy
    cat > "/tmp/trust-policy-$STAGE.json" << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:$REPO_OWNER/$REPO_NAME:ref:refs/heads/$BRANCH_PATTERN"
                }
            }
        }
    ]
}
EOF

    # Create permissions policy
    cat > "/tmp/permissions-policy-$STAGE.json" << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowServerlessDeployment",
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateChangeSet",
                "cloudformation:DeleteChangeSet",
                "cloudformation:DescribeChangeSet",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStacks",
                "cloudformation:ExecuteChangeSet",
                "cloudformation:GetTemplate",
                "cloudformation:ListStackResources",
                "cloudformation:UpdateStack",
                "cloudformation:CreateStack",
                "cloudformation:DeleteStack",
                "iam:PassRole",
                "iam:GetRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "lambda:*",
                "apigateway:*",
                "dynamodb:*",
                "logs:*",
                "events:*"
            ],
            "Resource": "*",
            "Condition": {
                "StringLike": {
                    "aws:RequestedRegion": "us-east-1"
                }
            }
        },
        {
            "Sid": "AllowS3FrontendDeployment",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::civicforge-frontend-$STAGE",
                "arn:aws:s3:::civicforge-frontend-$STAGE/*"
            ]
        },
        {
            "Sid": "AllowCloudFrontAccess",
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateInvalidation",
                "cloudfront:GetDistribution",
                "cloudfront:ListDistributions"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AllowSSMParameterAccess",
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:PutParameter"
            ],
            "Resource": "arn:aws:ssm:us-east-1:$AWS_ACCOUNT_ID:parameter/civicforge/$STAGE/*"
        }
    ]
}
EOF

    # Create or update the role
    if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "Updating existing role: $ROLE_NAME"
        aws iam update-assume-role-policy --role-name "$ROLE_NAME" --policy-document "file:///tmp/trust-policy-$STAGE.json"
    else
        echo "Creating new role: $ROLE_NAME"
        aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "file:///tmp/trust-policy-$STAGE.json"
    fi
    
    # Attach permissions policy
    aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "DeploymentPermissions" --policy-document "file:///tmp/permissions-policy-$STAGE.json"
    
    echo "✅ Role created: arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"
    
    # Clean up temp files
    rm "/tmp/trust-policy-$STAGE.json" "/tmp/permissions-policy-$STAGE.json"
}

# Create roles for each environment
create_deployment_role "dev" "develop"
create_deployment_role "staging" "staging"  
create_deployment_role "prod" "main"

echo ""
echo "🎉 OIDC Setup Complete!"
echo "======================"
echo ""
echo "Next steps:"
echo "1. Go to GitHub Repository Settings > Environments"
echo "2. Create environments: development, staging, production"
echo "3. Add environment secrets:"
echo ""
echo "   Environment: development"
echo "   Secret: AWS_ROLE_TO_ASSUME"
echo "   Value: arn:aws:iam::$AWS_ACCOUNT_ID:role/civicforge-deploy-dev"
echo ""
echo "   Environment: staging"
echo "   Secret: AWS_ROLE_TO_ASSUME"
echo "   Value: arn:aws:iam::$AWS_ACCOUNT_ID:role/civicforge-deploy-staging"
echo ""
echo "   Environment: production"
echo "   Secret: AWS_ROLE_TO_ASSUME"
echo "   Value: arn:aws:iam::$AWS_ACCOUNT_ID:role/civicforge-deploy-prod"
echo ""
echo "4. Delete the old repository secrets:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo ""
echo "5. Test the deployment by pushing to a branch or manually triggering the workflow"
echo ""
echo "🔒 Your CI/CD pipeline is now secure with OIDC!"