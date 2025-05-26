# Comprehensive AWS Docker ECS Fargate Deployment Guide for CivicForge MVP

This guide walks through setting up the necessary AWS infrastructure, building a Docker image, and deploying the CivicForge Board application using Fargate, RDS, and other AWS services.

### **Prerequisites**

* **AWS CLI:** Installed and configured with credentials that have appropriate permissions for ECR, ECS, RDS, IAM, Secrets Manager, VPC, and EC2.
* **Docker:** Installed and running on your local machine.
* **OpenSSL:** Installed (used for generating a random database password).
* Your application code, including a `Dockerfile`.

---

## Phase 1: Initial AWS Infrastructure Setup

These commands set up essential variables and foundational AWS resources. Perform these steps in order.

### **Step 0: Environment Variables & Initial Setup**

```bash
# Set your AWS region (e.g., us-east-1, us-west-2)
export REGION=us-east-1

# Find your AWS account ID, which is used in ARNs and ECR URIs
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)

# This command finds the default VPC ID and exports the variable
export VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $REGION)
echo "Using VPC with ID: $VPC_ID"

# --- Naming Conventions
export REPO_NAME=civicforge-board-mvp
export CLUSTER_NAME=civicforge-cluster
export SERVICE_NAME=civicforge-board-service
export TASK_DEF_FAMILY=civicforge-board-mvp
export DB_INSTANCE_IDENTIFIER=civicforge-db
export DB_MASTER_USERNAME=civicforge

# --- VPC and Networking
# Get available subnets in the default VPC and read them into an array
# This version works in sh, zsh, and bash

# Set positional parameters ($1, $2, $3...) to the output of the aws command
set -- $(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION)

if [ "$#" -lt 1 ]; then
  echo "Error: No subnets found in the default VPC ($VPC_ID) in region $REGION."
  echo "Please ensure your default VPC has at least one subnet."
  exit 1
fi

export SUBNET_1=$1
if [ "$#" -ge 2 ]; then
  export SUBNET_2=$2
  echo "Using SUBNET_1=$SUBNET_1 and SUBNET_2=$SUBNET_2"
else
  export SUBNET_2="" # No second subnet
  echo "Using SUBNET_1=$SUBNET_1 (Only one subnet found/selected)"
fi

# --- Create Application Security Group
# This SG allows public internet traffic to reach your application.
export APP_SG_ID=$(aws ec2 create-security-group \
  --group-name civicforge-app-sg \
  --description "Allows HTTP/S traffic to the CivicForge app" \
  --vpc-id $VPC_ID \
  --region $REGION \
  --query 'GroupId' --output text)

# Or, if the SG already exists.
export APP_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=civicforge-app-sg" \
  --query "SecurityGroups[0].GroupId" \
  --output text \
  --region $REGION)

# Open ports 80 (HTTP) and 443 (HTTPS) to the world (0.0.0.0/0)
aws ec2 authorize-security-group-ingress --group-id $APP_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION
aws ec2 authorize-security-group-ingress --group-id $APP_SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $REGION

echo "Created application security group: $APP_SG_ID"
```

### **Step 1: Create ECR Repository**

This repository will store your application's Docker images.

```bash
# Create ECR repository (if it doesn't already exist)
aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION > /dev/null 2>&1
if [ $? -ne 0 ]; then
  aws ecr create-repository \
    --repository-name $REPO_NAME \
    --image-tag-mutability MUTABLE \
    --region $REGION
  echo "ECR repository $REPO_NAME created."
else
  echo "ECR repository $REPO_NAME already exists."
fi
```

---

## Phase 2: Docker Image Preparation

### **Step 2: Build and Push Docker Image to ECR**

This step ensures your application's Docker image is built with the correct name and pushed to the Amazon ECR repository you created in Phase 1.

Ensure your `Dockerfile` is in the current directory and that your `$REGION`, `$ACCOUNT_ID`, and `$REPO_NAME` variables are set correctly from the previous steps.

This script combines login, build, tag, and push into a single, verifiable block. Copy the entire block and run it at once.

```bash
# Set the script to exit immediately if any command fails
set -e

# --- Authenticate, Build, Tag, and Push ---

echo "--- Step A: Logging in to ECR ---"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

echo
echo "--- Step B: Building Docker image with the correct name: $REPO_NAME ---"
docker build -t "$REPO_NAME:latest" .

echo
echo "--- Step C: Verifying the built image name ---"
echo "Looking for an image EXACTLY named '$REPO_NAME'..."
# This command should output at least one line with your image details
docker images "$REPO_NAME"

echo
echo "--- Step D: Tagging and pushing the correctly named image ---"
ECR_IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest"
echo "Tagging with URI: $ECR_IMAGE_URI"
docker tag "$REPO_NAME:latest" "$ECR_IMAGE_URI"

echo "Pushing to ECR..."
docker push "$ECR_IMAGE_URI"

echo
echo "✅ --- Docker image pushed to ECR successfully! --- ✅"
```

---

## Phase 3: Backend and Data Storage Setup

### **Step 3: Create Security Group for RDS**

This security group will protect your database, allowing access only from your application.

```bash
export DB_SG_ID=$(aws ec2 create-security-group \
  --group-name civicforge-db-sg \
  --description "Allows application traffic to the PostgreSQL DB" \
  --vpc-id $VPC_ID \
  --region $REGION \
  --query 'GroupId' --output text)

# BEST PRACTICE: Allow Postgres traffic ONLY from the application's security group.
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $APP_SG_ID \
  --region $REGION

echo "Created database security group: $DB_SG_ID"
```

### **Step 4: Generate Secure Database Password**

We will generate a strong random password for the RDS instance.

```bash
export DB_PASSWORD=$(openssl rand -base64 24)
echo "Generated a temporary database password. It will be stored in Secrets Manager."
# For security, avoid echoing the password directly to logs in CI/CD environments.
# Consider `echo "DB_PASSWORD set."` in such cases.
```

### **Step 5: Create RDS PostgreSQL Instance**

This command provisions a PostgreSQL database instance.

```bash
aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username $DB_MASTER_USERNAME \
    --master-user-password $DB_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids $DB_SG_ID \
    --no-publicly-accessible \
    --region $REGION
```

> **Important:** The `--master-user-password` parameter was missing in the original command, which would cause the database creation to fail.

### **Step 6: Wait for and Retrieve the DB Endpoint**

The database will take several minutes to create.

```bash
echo "Waiting for DB instance ($DB_INSTANCE_IDENTIFIER) to become available (this may take 5-10 minutes)..."
aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_IDENTIFIER --region $REGION

export DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
  --query "DBInstances[0].Endpoint.Address" \
  --output text --region $REGION)

echo "✅ Database is available at: $DB_ENDPOINT"
```

### **Step 7: Create Secrets in AWS Secrets Manager**

Store sensitive data like your database URL (with the generated password) and application secret key.

```bash
# Database URL secret (using the generated DB_PASSWORD)
# NOTE: Using the default 'postgres' database which always exists
DB_SECRET_ARN=$(aws secretsmanager create-secret \
    --name civicforge/database-url \
    --description "Database connection string for CivicForge" \
    --secret-string "postgresql://$DB_MASTER_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:5432/postgres" \
    --region $REGION \
    --query ARN --output text)
echo "Database URL Secret ARN: $DB_SECRET_ARN"
echo "Note: Using the default 'postgres' database. The application will create its tables automatically on first run."


# Application secret key (for session management, etc.)
APP_SECRET_KEY_ARN=$(aws secretsmanager create-secret \
    --name civicforge/secret-key \
    --description "Application secret key for CivicForge" \
    --secret-string "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
    --region $REGION \
    --query ARN --output text)
echo "Application Secret Key ARN: $APP_SECRET_KEY_ARN"
```

> **Note:** After the RDS instance is created, connect to it (e.g., using `psql` with `$DB_MASTER_USERNAME` and the generated `$DB_PASSWORD`) to create the actual database (e.g., `civicforge_db_db` or your desired name) if your application doesn't handle this.

---

## Phase 4: ECS Configuration and IAM Roles

### **Step 8: Create ECS Cluster**

An ECS cluster is a logical grouping for your services and tasks.

```bash
aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $REGION
```

### **Step 9: Create Required IAM Roles (Shell-Compatible Version)**

ECS requires two IAM roles. We will create them by first saving their policies to temporary files to ensure compatibility across all command-line shells.

#### **Task Execution Role**
*Allows ECS to pull images, manage logs, and access secrets.*

```bash
# --- Create the Task Execution Role ---

# First, create the trust policy JSON file
cat > civicforge-task-exec-trust-policy.json << EOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ecs-tasks.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOL

# Now, create the role using the policy file
aws iam create-role \
  --role-name civicforge-task-execution-role \
  --assume-role-policy-document file://civicforge-task-exec-trust-policy.json \
  --description "Allows ECS tasks to call AWS services on your behalf." \
  --region $REGION

# Attach the standard AWS-managed policy
aws iam attach-role-policy \
  --role-name civicforge-task-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
  --region $REGION

# --- Create and attach custom policy for Secrets Manager access ---

# First, create the secrets access policy JSON file
cat > civicforge-exec-secrets-policy.json << EOL
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": [
                "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:civicforge/database-url-*",
                "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:civicforge/secret-key-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "kms:Decrypt",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": "secretsmanager.$REGION.amazonaws.com"
                }
            }
        }
    ]
}
EOL

# Create the policy from the JSON file
TASK_EXECUTION_SECRETS_POLICY_ARN=$(aws iam create-policy \
  --policy-name CivicForgeExecutionSecretsAccess \
  --policy-document file://civicforge-exec-secrets-policy.json \
  --query Policy.Arn --output text --region $REGION)

# Attach the new custom policy to the role
aws iam attach-role-policy \
  --role-name civicforge-task-execution-role \
  --policy-arn $TASK_EXECUTION_SECRETS_POLICY_ARN \
  --region $REGION

echo "Task Execution Role created and configured."
```

#### **Task Role**

Grants permissions to the application code *inside* your container.

```bash
# --- Create the Task Role ---

# First, create the trust policy JSON file for the role itself
cat > civicforge-task-trust-policy.json << EOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ecs-tasks.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOL

# Now, create the role using the policy file
aws iam create-role \
  --role-name civicforge-task-role \
  --assume-role-policy-document file://civicforge-task-trust-policy.json \
  --description "Allows the application within the ECS task to call AWS services." \
  --region $REGION

# --- Create and attach custom policy for the application to access its secrets ---

# First, create the secrets access policy JSON file
cat > civicforge-task-secrets-policy.json << EOL
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": [
                "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:civicforge/database-url-*",
                "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:civicforge/secret-key-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "kms:Decrypt",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": "secretsmanager.$REGION.amazonaws.com"
                }
            }
        }
    ]
}
EOL

# Create the policy from the JSON file
TASK_ROLE_SECRETS_POLICY_ARN=$(aws iam create-policy \
  --policy-name CivicForgeTaskSecretsAccess \
  --policy-document file://civicforge-task-secrets-policy.json \
  --query Policy.Arn --output text --region $REGION)

# Attach the new custom policy to the role
aws iam attach-role-policy \
  --role-name civicforge-task-role \
  --policy-arn $TASK_ROLE_SECRETS_POLICY_ARN \
  --region $REGION

echo "Task Role created and configured."
```

### **Step 10: Find and Store Role ARNs**

Fetch the ARNs for the created roles.

```bash
export TASK_EXECUTION_ROLE_ARN=$(aws iam get-role --role-name civicforge-task-execution-role --query 'Role.Arn' --output text --region $REGION)
export TASK_ROLE_ARN=$(aws iam get-role --role-name civicforge-task-role --query 'Role.Arn' --output text --region $REGION)

echo "Task Execution Role ARN: $TASK_EXECUTION_ROLE_ARN"
echo "Task Role ARN: $TASK_ROLE_ARN"
```

---

## Phase 5: Application Deployment

### **Step 11: Prepare and Register ECS Fargate Task Definition**

The task definition is a blueprint for your application.

#### **1. Create `ecs-task-definition.json`:**

Create a file named `ecs-task-definition.json` with the following content.

```json
{
  "family": "civicforge-board-mvp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "YOUR_TASK_EXECUTION_ROLE_ARN_PLACEHOLDER",
  "taskRoleArn": "YOUR_TASK_ROLE_ARN_PLACEHOLDER",
  "containerDefinitions": [
    {
      "name": "civicforge-app",
      "image": "YOUR_ECR_IMAGE_URI_PLACEHOLDER",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/civicforge-board-mvp",
          "awslogs-region": "YOUR_AWS_REGION_PLACEHOLDER",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

> **Note on Secrets:** If you want to inject secrets from AWS Secrets Manager directly as environment variables into your container, add a `secrets` array to the `containerDefinitions` object. Example:
>
> ```json
>       "secrets": [
>         {
>           "name": "DATABASE_URL_ENV_VAR",
>           "valueFrom": "YOUR_ACTUAL_DB_SECRET_ARN"
>         },
>         {
>           "name": "APPLICATION_SECRET_KEY_ENV_VAR",
>           "valueFrom": "YOUR_ACTUAL_APP_SECRET_KEY_ARN"
>         }
>       ]
> ```

#### **2. Replace placeholders in `ecs-task-definition.json`:**

Manually edit the `ecs-task-definition.json` file.

* Replace `YOUR_TASK_EXECUTION_ROLE_ARN_PLACEHOLDER` with the value of `$TASK_EXECUTION_ROLE_ARN`.
* Replace `YOUR_TASK_ROLE_ARN_PLACEHOLDER` with the value of `$TASK_ROLE_ARN`.
* Replace `YOUR_ECR_IMAGE_URI_PLACEHOLDER` with the value of `$ECR_IMAGE_URI`.
* Replace `YOUR_AWS_REGION_PLACEHOLDER` with `$REGION`.

> **Best Practice:** Add `ecs-task-definition.json` to your `.gitignore` file. Commit a template version (e.g., `ecs-task-definition.json.template`) to source control.

#### **3. Register the task definition:**

```bash
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region $REGION
```

### **Step 12: Create ECS Fargate Service**

This launches your container and makes it accessible.

```bash
# Construct the subnets string
SUBNETS_CONFIG="subnets=[$SUBNET_1]"
if [ -n "$SUBNET_2" ]; then
  SUBNETS_CONFIG="subnets=[$SUBNET_1,$SUBNET_2]"
fi

echo "Attempting to create/update service with SUBNETS_CONFIG: $SUBNETS_CONFIG and APP_SG_ID: $APP_SG_ID"
if [ -z "$APP_SG_ID" ]; then
  echo "Error: APP_SG_ID is not set. Please check Step 0 for security group creation."
  exit 1
fi

aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_DEF_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={$SUBNETS_CONFIG,securityGroups=[$APP_SG_ID],assignPublicIp=ENABLED}" \
  --region $REGION
```

> **Note:** `assignPublicIp=ENABLED` is for MVP. For production, an Application Load Balancer is recommended.

---

## Phase 6: Post-Deployment and Monitoring

### **Step 13: Find Your Application's Public IP**

```bash
echo "Waiting for service ($SERVICE_NAME) to become stable (this might take a few minutes)..."
aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION

echo "Finding task ENI..."
TASK_ARN_OUTPUT=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query 'taskArns[0]' --output text --region $REGION)

if [ -z "$TASK_ARN_OUTPUT" ] || [ "$TASK_ARN_OUTPUT" == "None" ] || [ "$TASK_ARN_OUTPUT" == "null" ]; then
  echo "Error: No running tasks found for service $SERVICE_NAME."
  exit 1
fi

ENI_ID_OUTPUT=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN_OUTPUT --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value | [0]' --output text --region $REGION)

if [ -z "$ENI_ID_OUTPUT" ] || [ "$ENI_ID_OUTPUT" == "None" ] || [ "$ENI_ID_OUTPUT" == "null" ]; then
  echo "Error: Could not find ENI for task $TASK_ARN_OUTPUT."
  exit 1
fi

echo "Fetching public IP for ENI $ENI_ID_OUTPUT..."
PUBLIC_IP_OUTPUT=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID_OUTPUT --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region $REGION)

if [ -z "$PUBLIC_IP_OUTPUT" ] || [ "$PUBLIC_IP_OUTPUT" == "None" ] || [ "$PUBLIC_IP_OUTPUT" == "null" ]; then
  echo "Error: Could not find Public IP for ENI $ENI_ID_OUTPUT. Ensure assignPublicIp was ENABLED."
  exit 1
fi

echo "✅ Application Public IP: $PUBLIC_IP_OUTPUT"
echo "Access your application at http://$PUBLIC_IP_OUTPUT:8000 (or the hostPort you configured)"
```

### **Step 14: Monitoring**

#### **CloudWatch Logs**

View application logs (ensure `logConfiguration` in the task definition is correct).

```bash
aws logs tail /ecs/$TASK_DEF_FAMILY --follow --region $REGION
```

#### **ECS Service Status**

```bash
aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION
```

---

## Ongoing Operations

### **Deployment Updates**

1.  Build and push a new Docker image version to ECR (e.g., `$REPO_NAME:v1.1`).
2.  Create a new revision of your ECS Task Definition with the updated image URI.
3.  Update the ECS Service to use the new task definition revision:

```bash
# Example: Update service to use the latest active revision
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition $TASK_DEF_FAMILY \
  --force-new-deployment \
  --region $REGION
```

---

## Security Best Practices Summary

* **Least Privilege:** IAM roles and policies should grant only necessary permissions.
* **Secrets Management:** Store all sensitive data (DB credentials, API keys) in AWS Secrets Manager.
* **HTTPS:** For production, always use HTTPS with an Application Load Balancer (ALB) and AWS Certificate Manager (ACM).
* **Network Security:** Use restrictive security groups and run RDS in private subnets.
* **Container Security:** Run application processes as a non-root user and regularly scan images for vulnerabilities.
* **Logging & Monitoring:** Enable VPC Flow Logs, CloudTrail, and monitor application and infrastructure health.
* **Regularly Rotate Secrets.**

---

## Cost Optimization

* **Fargate Spot:** For non-production or fault-tolerant workloads.
* **Right-sizing:** Adjust Fargate task CPU/memory and RDS instance sizes.
* **Aurora Serverless v2:** For variable database workloads.
* **Auto-scaling:** For ECS services.

---

## Backup and Recovery

* **RDS Automated Backups:** Enabled by default. Verify retention settings.
* **Manual Snapshots:** Take snapshots before major changes.
* **Infrastructure as Code (IaC):** Use CloudFormation, CDK, or Terraform for reproducibility.
* **Test Restore Procedures.**

---

## Troubleshooting Common Issues

### Database Connection Errors
* **"database does not exist"**: The application uses the default `postgres` database. If you see this error, check that the DATABASE_URL secret is using `postgres` as the database name.
* **"role cannot be assumed"**: Ensure the ECS task execution role name in the task definition matches exactly: `civicforge-task-execution-role` (not `civicforge-execution-role`).

### Application Access Issues
* **Cannot access the application**: By default, the security group allows access from all IPs. To restrict access:
  ```bash
  # Remove open access
  aws ec2 revoke-security-group-ingress --group-id $APP_SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $REGION
  
  # Add your IP only
  MY_IP=$(curl -s https://api.ipify.org)
  aws ec2 authorize-security-group-ingress --group-id $APP_SG_ID --protocol tcp --port 8000 --cidr ${MY_IP}/32 --region $REGION
  ```

### Default Users
* The application creates default users automatically on first deployment:
  - Username: `admin`, Password: `admin123`
  - Username: `dev`, Password: `dev123`
* If users are not created, check the deployment logs or manually call the `/api/init-default-users` endpoint.