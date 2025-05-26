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

# Build and push a platform-specific image to ECR
echo -e "${GREEN}Building and pushing AMD64-compatible image to ECR...${NC}"
docker buildx build --platform linux/amd64 -t "${ECR_URI}:latest" --push .

# Update task definition with new image
echo -e "${GREEN}Updating ECS task definition...${NC}"
# Create a temporary copy of the template
cp deploy/aws/ecs-task-definition.json.template deploy/aws/ecs-task-definition.json
# Replace placeholders in the copy
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
rm deploy/aws/ecs-task-definition.json
rm deploy/aws/ecs-task-definition.json.bak

# Initialize default users if needed
echo -e "${YELLOW}Waiting for service to be ready...${NC}"
sleep 30

# Get the task IP
TASK_ARN=$(aws ecs list-tasks --cluster ${ECS_CLUSTER} --service-name ${ECS_SERVICE} --desired-status RUNNING --query 'taskArns[0]' --output text --region ${AWS_REGION})
if [ -n "$TASK_ARN" ] && [ "$TASK_ARN" != "None" ]; then
    ENI_ID=$(aws ecs describe-tasks --cluster ${ECS_CLUSTER} --tasks ${TASK_ARN} --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value | [0]' --output text --region ${AWS_REGION})
    if [ -n "$ENI_ID" ] && [ "$ENI_ID" != "None" ]; then
        PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids ${ENI_ID} --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region ${AWS_REGION})
        if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "None" ]; then
            echo -e "${GREEN}Service is available at: http://${PUBLIC_IP}:8000${NC}"
            
            # Initialize default users
            echo -e "${YELLOW}Initializing default users...${NC}"
            curl -s -X POST "http://${PUBLIC_IP}:8000/api/init-default-users" -H "Content-Type: application/json" || echo "Could not initialize users (this is normal if they already exist)"
        fi
    fi
fi