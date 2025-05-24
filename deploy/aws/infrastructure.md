# AWS Infrastructure Setup for CivicForge Board MVP

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed
3. AWS account with appropriate permissions

## Initial Setup (One-time)

### 1. Create ECR Repository

```bash
aws ecr create-repository \
    --repository-name civicforge-board-mvp \
    --region us-east-1
```

### 2. Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
    --db-instance-identifier civicforge-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.3 \
    --master-username civicforge \
    --master-user-password CHANGE_THIS_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-YOUR_SECURITY_GROUP \
    --backup-retention-period 7 \
    --publicly-accessible false
```

### 3. Create Secrets in AWS Secrets Manager

```bash
# Database URL
aws secretsmanager create-secret \
    --name civicforge/database-url \
    --secret-string "postgresql://civicforge:PASSWORD@your-rds-endpoint:5432/civicforge_db"

# Secret Key
aws secretsmanager create-secret \
    --name civicforge/secret-key \
    --secret-string "$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

### 4. Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name civicforge-cluster
```

### 5. Create Application Load Balancer

```bash
# Create ALB (use AWS Console for easier setup)
# Configure:
# - Internet-facing
# - HTTP listener on port 80
# - HTTPS listener on port 443 (with ACM certificate)
# - Target group for port 8000
```

### 6. Create ECS Service

```bash
aws ecs create-service \
    --cluster civicforge-cluster \
    --service-name civicforge-board-service \
    --task-definition civicforge-board-mvp:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=civicforge-app,containerPort=8000"
```

### 7. Create IAM Roles

#### Task Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Attach policies:
- `AmazonECSTaskExecutionRolePolicy`
- Custom policy for Secrets Manager access

#### Task Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:civicforge/*"
      ]
    }
  ]
}
```

## Deployment

After initial setup, use the deployment script:

```bash
./deploy/aws/deploy.sh
```

## Monitoring

### CloudWatch Logs
```bash
aws logs tail /ecs/civicforge-board-mvp --follow
```

### ECS Service Status
```bash
aws ecs describe-services \
    --cluster civicforge-cluster \
    --services civicforge-board-service
```

## Cost Optimization

- Use Fargate Spot for non-production environments
- Consider Aurora Serverless v2 for variable workloads
- Enable auto-scaling based on CPU/memory metrics
- Use CloudFront for static assets

## Security Checklist

- [ ] RDS is in private subnet
- [ ] Security groups restrict access appropriately
- [ ] Secrets are stored in AWS Secrets Manager
- [ ] HTTPS is enforced via ALB
- [ ] WAF rules are configured
- [ ] VPC flow logs are enabled
- [ ] CloudTrail is logging API calls

## Backup and Recovery

- RDS automated backups: 7 days retention
- Manual snapshots before major updates
- Database migration scripts in version control
- Regular testing of restore procedures