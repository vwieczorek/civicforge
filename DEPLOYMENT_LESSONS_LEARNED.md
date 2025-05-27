# CivicForge Deployment Lessons Learned
*Critical knowledge for successful AWS ECS deployments*

## 🚨 Key Issues and Solutions

### 1. Health Check Failures
**Problem**: ECS tasks were constantly restarting due to health check failures.

**Root Causes**:
- Health check endpoint mismatch (`/api/health` vs `/health`)
- Using `curl` in health checks when it's not installed in the container
- Wrong health check command format in task definition

**Solutions**:
```json
// Correct health check in task definition
"healthCheck": {
  "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"],
  "interval": 30,
  "timeout": 5,
  "retries": 3,
  "startPeriod": 60
}
```

**Key Learning**: Always use Python's built-in `urllib` for health checks to avoid external dependencies.

### 2. Database Migrations Not Running
**Problem**: New tables weren't created, causing 500 errors on all new endpoints.

**Root Causes**:
- Dockerfile's CMD doesn't run shell scripts properly
- No startup script to run migrations before starting the app

**Solution**:
1. Created `docker-entrypoint.sh`:
```bash
#!/bin/bash
set -e

echo "Running database migrations..."
python -m src.board_mvp.migrations_pg

echo "Starting the application..."
exec uvicorn src.board_mvp.web:app --host 0.0.0.0 --port 8000
```

2. Updated Dockerfile:
```dockerfile
COPY docker-entrypoint.sh .
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
```

### 3. Missing Initial Board Owner
**Problem**: No users had permissions to create invites after deployment.

**Solution**: Added automatic board owner assignment in migrations:
```python
# In migrations_pg.py, after creating tables
existing_memberships = db.fetchone("SELECT COUNT(*) as count FROM board_memberships")
if existing_memberships and existing_memberships['count'] == 0:
    first_organizer = db.fetchone("""
        SELECT id FROM users 
        WHERE role = 'Organizer' 
        ORDER BY created_at ASC 
        LIMIT 1
    """)
    if first_organizer:
        from .auth import ROLE_PERMISSIONS
        owner_perms = ROLE_PERMISSIONS['owner']
        db.execute("""
            INSERT INTO board_memberships (board_id, user_id, role, permissions)
            VALUES (%s, %s, %s, %s::jsonb)
        """, ('board_001', first_organizer['id'], 'owner', json.dumps(owner_perms)))
```

### 4. Dynamic IP Address Changes
**Problem**: ECS tasks get new public IPs on each restart, breaking tests.

**Solution**: Always fetch the current IP before testing:
```bash
TASK_ARN=$(aws ecs list-tasks --cluster civicforge-cluster --service-name civicforge-board-service --desired-status RUNNING --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster civicforge-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
```

### 5. Docker Build Cache Issues
**Problem**: Changes weren't being deployed because Docker used cached layers.

**Solution**: Force rebuild without cache when critical changes are made:
```bash
docker build --no-cache --platform linux/amd64 -t $ECR_REPO:latest .
```

### 6. Architecture Mismatch (exec format error)
**Problem**: Tasks failing with "exec /bin/bash: exec format error" when built on Apple Silicon.

**Solution**: Always use buildx with platform specification:
```bash
docker buildx build --platform linux/amd64 -t $ECR_REPO:latest --push .
```

### 7. Database Adapter Compatibility
**Problem**: PostgreSQL adapter's cursor doesn't have `rowcount` attribute, causing 500 errors.

**Solution**: Check existence before operations instead of relying on rowcount:
```python
# Wrong - works with SQLite but not PostgreSQL
result = db.execute("DELETE FROM table WHERE id=?", (id,))
if result.rowcount == 0:
    raise HTTPException(404)

# Correct - works with both adapters
existing = db.fetchone("SELECT id FROM table WHERE id=?", (id,))
if not existing:
    raise HTTPException(404)
db.execute("DELETE FROM table WHERE id=?", (id,))
```

### 8. API Method Naming Bugs
**Problem**: Using `secrets.urlsafe()` instead of `secrets.token_urlsafe()` caused 500 errors.

**Solution**: Always verify Python API methods exist:
```python
# Wrong
token = secrets.urlsafe(32)  # AttributeError

# Correct
token = secrets.token_urlsafe(32)
```

## 📋 Deployment Checklist

### Before Deploying:
1. **Check Database Compatibility**
   - Ensure migrations support both PostgreSQL and SQLite
   - Use parameterized queries with correct placeholders (`%s` for PostgreSQL, `?` for SQLite)

2. **Verify Health Checks**
   - Confirm health endpoint exists and returns 200 OK
   - Use Python urllib, not curl
   - Match the exact endpoint path in task definition

3. **Test Locally with Docker**
   ```bash
   docker-compose up -d
   docker-compose logs -f app  # Watch for startup errors
   ```

### During Deployment:
1. **Build and Push**
   ```bash
   # Build for AMD64 (Fargate architecture)
   docker build --platform linux/amd64 -t $ECR_REPO:latest .
   
   # Push to ECR
   docker push $ECR_REPO:latest
   ```

2. **Update Task Definition**
   ```bash
   # Register new task definition
   aws ecs register-task-definition --cli-input-json file://deploy/aws/ecs-task-definition.json
   
   # Force new deployment
   aws ecs update-service --cluster civicforge-cluster --service civicforge-board-service --force-new-deployment
   ```

3. **Monitor Deployment**
   ```bash
   # Check service events
   aws ecs describe-services --cluster civicforge-cluster --services civicforge-board-service --query 'services[0].events[0:5]' --output table
   
   # Check CloudWatch logs
   TASK_ID=$(aws ecs list-tasks --cluster civicforge-cluster --service-name civicforge-board-service --query 'taskArns[0]' --output text | awk -F'/' '{print $NF}')
   aws logs tail /ecs/civicforge-board-mvp --log-stream-name-prefix "ecs/civicforge-app/$TASK_ID"
   ```

### After Deployment:
1. **Verify Health**
   ```bash
   # Get current public IP
   PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
   
   # Test health endpoint
   python -c "import urllib.request; print(urllib.request.urlopen('http://$PUBLIC_IP:8000/health').read().decode())"
   ```

2. **Run Tests**
   ```bash
   API_BASE_URL="http://$PUBLIC_IP:8000" python3 -m pytest tests/api/test_invites.py -v
   ```

## 🔍 Debugging Tips

### Common Error Patterns:

1. **"relation does not exist"**
   - Migrations didn't run
   - Check startup logs for migration output
   - Verify docker-entrypoint.sh is executable

2. **"No permission to..."**
   - User lacks board membership
   - Check board_memberships table
   - Verify first organizer was assigned as owner

3. **Task keeps restarting**
   - Health check failing
   - Check CloudWatch logs for startup errors
   - Verify health endpoint is accessible

4. **Changes not appearing**
   - Docker cache issue
   - Force rebuild with --no-cache
   - Verify ECR image was updated

5. **"exec format error"**
   - Wrong architecture (ARM vs AMD64)
   - Always use `--platform linux/amd64` when building
   - Check with: `docker image inspect $IMAGE | grep Architecture`

6. **500 errors on database operations**
   - Check CloudWatch logs for full traceback
   - Common issues: rowcount attribute, wrong SQL syntax
   - Test database operations locally first

### Useful Commands:
```bash
# Get all running task IDs
aws ecs list-tasks --cluster civicforge-cluster --service-name civicforge-board-service --desired-status RUNNING

# Check task health status
aws ecs describe-tasks --cluster civicforge-cluster --tasks $TASK_ARN --query 'tasks[0].healthStatus'

# Get container logs for debugging
aws logs get-log-events --log-group-name /ecs/civicforge-board-mvp --log-stream-name "ecs/civicforge-app/$TASK_ID" --start-from-head

# Check security group rules
aws ec2 describe-security-groups --group-ids $SG_ID --query 'SecurityGroups[0].IpPermissions'
```

## 🏗️ Architecture Notes

### Service Configuration:
- **Cluster**: civicforge-cluster
- **Service**: civicforge-board-service (not civicforge-board-mvp-service)
- **Task Definition**: civicforge-board-mvp
- **Log Group**: /ecs/civicforge-board-mvp
- **Port**: 8000
- **Platform**: Fargate with AMD64 architecture

### IAM Roles:
- **Task Execution Role**: civicforge-task-execution-role
- **Secrets**: Stored in AWS Secrets Manager at civicforge/board-mvp/*

### Database:
- **RDS Instance**: PostgreSQL 15.x
- **Connection**: Via DATABASE_URL from Secrets Manager
- **Migrations**: Run automatically on container startup

## 🚀 Deployment Time Estimates

- **Docker Build**: 1-2 minutes
- **ECR Push**: 30-60 seconds
- **Task Startup**: 2-3 minutes
- **Health Check Stabilization**: 1-2 minutes
- **Total Deployment Time**: 5-7 minutes

**Important**: Don't rush! Common mistakes:
- Testing before deployment completes (old code still running)
- Not waiting for health checks to pass
- Assuming first task that starts is healthy (may restart several times)

**Best Practice**: Use `aws ecs wait services-stable` or wait at least 3 minutes after deployment before testing.

## 📝 Final Notes

1. **Always use Python urllib** instead of curl for any HTTP operations in containers
2. **Document all environment variables** required for deployment
3. **Test migrations locally** with both SQLite and PostgreSQL before deploying
4. **Monitor CloudWatch logs** during deployment for early error detection
5. **Keep this document updated** with new learnings!

Remember: The deployment process has many moving parts. When something fails, check the logs first, then verify each component systematically.