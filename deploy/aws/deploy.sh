#!/bin/bash
# AWS ECS Deployment Script for CivicForge Board MVP

set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
ECR_REPOSITORY=${ECR_REPOSITORY:-"civicforge-board-mvp"}
ECS_CLUSTER=${ECS_CLUSTER:-"civicforge-cluster"}
ECS_SERVICE=${ECS_SERVICE:-"civicforge-board-service"}
TASK_DEFINITION_FAMILY="civicforge-board-mvp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CivicForge Board MVP deployment...${NC}"

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo -e "${YELLOW}ECR Repository: ${ECR_URI}${NC}"

# Login to ECR
echo -e "${GREEN}Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Build Docker image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t ${ECR_REPOSITORY}:latest .

# Tag image for ECR
docker tag ${ECR_REPOSITORY}:latest ${ECR_URI}:latest

# Push image to ECR
echo -e "${GREEN}Pushing image to ECR...${NC}"
docker push ${ECR_URI}:latest

# Update task definition with new image
echo -e "${GREEN}Updating ECS task definition...${NC}"
sed -i.bak "s|YOUR_ACCOUNT_ID|${AWS_ACCOUNT_ID}|g" deploy/aws/ecs-task-definition.json
sed -i.bak "s|YOUR_ECR_REPO_URI|${ECR_URI}|g" deploy/aws/ecs-task-definition.json

# Register new task definition
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://deploy/aws/ecs-task-definition.json \
    --region ${AWS_REGION} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo -e "${YELLOW}New task definition: ${TASK_DEFINITION_ARN}${NC}"

# Update ECS service with new task definition
echo -e "${GREEN}Updating ECS service...${NC}"
aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${ECS_SERVICE} \
    --task-definition ${TASK_DEFINITION_ARN} \
    --force-new-deployment \
    --region ${AWS_REGION}

echo -e "${GREEN}Deployment initiated! Monitor progress in AWS Console.${NC}"

# Wait for service to stabilize (optional)
echo -e "${YELLOW}Waiting for service to stabilize...${NC}"
aws ecs wait services-stable \
    --cluster ${ECS_CLUSTER} \
    --services ${ECS_SERVICE} \
    --region ${AWS_REGION}

echo -e "${GREEN}Deployment complete!${NC}"

# Restore original task definition file
mv deploy/aws/ecs-task-definition.json.bak deploy/aws/ecs-task-definition.json