# CivicForge Docker Deployment Guide
*Production-Ready Docker Setup*

## 🐳 Why Docker is Preferred

Docker is now the **recommended deployment method** for CivicForge because:

- ✅ **5-second setup** - `docker-compose up -d` starts everything
- ✅ **PostgreSQL production backend** - Real database, not SQLite
- ✅ **Health monitoring** - Built-in container health checks
- ✅ **Environment isolation** - No local Python/PostgreSQL setup needed
- ✅ **Production parity** - Same stack as AWS deployment
- ✅ **Zero configuration** - Everything pre-configured and tested

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git (to clone the repository)

### Launch in 5 Seconds
```bash
git clone <repository-url>
cd civicforge
docker-compose up -d
open http://localhost:8000
```

### Default Access
- **URL**: http://localhost:8000
- **Admin**: username `admin`, password `admin123` (20 XP)
- **Dev**: username `dev`, password `dev123` (0 XP)

## 📋 What Gets Started

### Services
- **PostgreSQL Database** (port 5432)
  - Database: `civicforge_db`
  - User: `civicforge`
  - Health checks enabled
  
- **CivicForge Application** (port 8000)
  - Web interface + API endpoints
  - Automatic database migrations
  - Health monitoring at `/api/health`

### Data Persistence
- PostgreSQL data persists in Docker volume `postgres_data`
- Survives container restarts and rebuilds
- Use `docker-compose down -v` to reset all data

## 🔧 Development Workflow

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
```

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it civicforge-postgres-1 psql -U civicforge -d civicforge_db

# Check tables
\dt

# View users
SELECT id, username, role, verified FROM users;
```

### Restart Services
```bash
# Restart everything
docker-compose restart

# Restart specific service
docker-compose restart app
docker-compose restart postgres
```

### Update Code
```bash
# Rebuild after code changes
docker-compose build app
docker-compose up app -d
```

## 🏥 Health Monitoring

### Check Container Health
```bash
docker ps  # Shows health status
docker-compose ps  # Shows service status
```

### Health Endpoints
- **Application**: `curl http://localhost:8000/api/health`
- **Database**: Automatic health checks in docker-compose

### Troubleshooting
```bash
# View container health details
docker inspect civicforge-app-1 | grep -A 10 Health
docker inspect civicforge-postgres-1 | grep -A 10 Health

# Check resource usage
docker stats civicforge-app-1 civicforge-postgres-1
```

## 🔄 Development vs Production

### Development (Current)
```yaml
# docker-compose.yml - development optimized
- Volume mounts for live code reloading
- Development secret keys
- Exposed database ports
- Console logging
```

### Production (AWS)
```yaml
# Use same containers but with:
- Environment variables from AWS Secrets Manager
- RDS PostgreSQL instead of container
- Load balancer health checks
- CloudWatch logging
```

## 🛠️ Customization

### Environment Variables
Create `.env` file:
```bash
CIVICFORGE_SECRET_KEY=your-32-character-secret-key
TOKEN_EXPIRY_HOURS=24
DATABASE_URL=postgresql://civicforge:password@postgres:5432/civicforge_db
```

### Port Changes
Edit `docker-compose.yml`:
```yaml
ports:
  - "3000:8000"  # Access on port 3000 instead
```

### Resource Limits
Add to `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

## 🚀 Deployment Pipeline

### Development → Staging → Production

1. **Development**: `docker-compose up -d` (local)
2. **Staging**: Deploy to staging AWS with same Docker images
3. **Production**: Deploy to production AWS with same Docker images

Same containers, different environments = reliable deployments.

## 📊 Monitoring

### Container Metrics
```bash
# CPU, Memory, Network usage
docker stats

# Container health over time
docker events --filter container=civicforge-app-1
```

### Application Metrics
- Health check: `GET /api/health`
- User count: `GET /api/stats/board`
- Database connectivity: Automatic monitoring

## 🔒 Security Notes

### Development Security
- Default passwords are for development only
- PostgreSQL not exposed to external network by default
- Application runs as non-root user in container

### Production Security
- Use AWS Secrets Manager for all credentials
- Enable HTTPS/SSL termination at load balancer
- Use RDS with encryption at rest
- Network isolation with VPC

## 🎯 Next Steps

1. **Test the Docker setup** - Verify everything works
2. **Develop features** - Use Docker for all development
3. **Deploy to AWS** - Follow `deploy/aws/infrastructure.md`
4. **Monitor production** - Set up CloudWatch, Sentry

Docker provides the foundation for reliable, scalable deployment from development through production.