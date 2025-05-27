# CivicForge Deployment Quick Reference

## 🚀 Deploy Updates to AWS

```bash
# 1. Build and push image (ALWAYS with platform flag!)
cd /Users/victor/Projects/civicforge
docker buildx build --platform linux/amd64 -t $ECR_REPO:latest --push .

# 2. Force new deployment
aws ecs update-service --cluster civicforge-cluster --service civicforge-board-service --force-new-deployment --region us-east-1

# 3. Wait for deployment (3-5 minutes)
aws ecs wait services-stable --cluster civicforge-cluster --services civicforge-board-service --region us-east-1

# 4. Get new IP address
TASK_ARN=$(aws ecs list-tasks --cluster civicforge-cluster --service-name civicforge-board-service --desired-status RUNNING --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster civicforge-cluster --tasks "$TASK_ARN" --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
echo "New deployment URL: http://$PUBLIC_IP:8000"
```

## 🧪 Test Deployment

```bash
# Quick health check
curl http://$PUBLIC_IP:8000/api/health

# Run full test suite
API_URL=http://$PUBLIC_IP:8000 python src/board_mvp/test_full_invites.py
```

## 🔍 Debug Issues

```bash
# Check service events
aws ecs describe-services --cluster civicforge-cluster --services civicforge-board-service --query 'services[0].events[0:5]' --output table

# Get task logs
TASK_ID=$(echo $TASK_ARN | awk -F'/' '{print $NF}')
aws logs tail /ecs/civicforge-board-mvp --log-stream-name-prefix "ecs/civicforge-app/$TASK_ID" --since 5m

# Check for errors
aws logs tail /ecs/civicforge-board-mvp --since 10m --format short | grep -i error
```

## 📊 Current Infrastructure

- **Cluster**: civicforge-cluster
- **Service**: civicforge-board-service  
- **Task Definition**: civicforge-board-mvp
- **ECR Repository**: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/civicforge-board-mvp
- **Log Group**: /ecs/civicforge-board-mvp
- **Database**: RDS PostgreSQL (civicforge-db)

## ⚠️ Remember

1. **Always use `--platform linux/amd64`** for Docker builds
2. **Wait for deployment to complete** before testing
3. **Check CloudWatch logs** if something fails
4. **IP address changes** with each deployment
5. **Use Python urllib** not curl for health checks