# Local Development Setup Tutorial

This tutorial will guide you through setting up CivicForge for local development.

## Overview

CivicForge consists of:
- **Backend**: Python/FastAPI serverless functions
- **Frontend**: React 18 with Vite
- **Infrastructure**: AWS services (DynamoDB, Cognito, Lambda)

## Prerequisites

### Required Software
- Node.js 18+ ([download](https://nodejs.org/))
- Python 3.11+ ([download](https://www.python.org/))
- AWS CLI ([install guide](https://aws.amazon.com/cli/))
- Docker (for local DynamoDB)

### Recommended Tools
- VS Code with extensions:
  - Python
  - ESLint
  - Prettier
  - AWS Toolkit

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/civicforge.git
cd civicforge
```

## Step 2: Backend Setup

### Create Python Virtual Environment

```bash
cd backend
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
npm install  # For serverless framework
```

### Configure Environment

Create `backend/.env`:
```bash
STAGE=local
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=local-pool-id
COGNITO_APP_CLIENT_ID=local-client-id
USERS_TABLE=civicforge-local-users
QUESTS_TABLE=civicforge-local-quests
FAILED_REWARDS_TABLE=civicforge-local-failed-rewards
```

### Start Local DynamoDB

```bash
# Using Docker
docker run -p 8000:8000 amazon/dynamodb-local

# Or using serverless-dynamodb-local
serverless dynamodb install
serverless dynamodb start
```

### Run Backend Locally

```bash
# Start the API
serverless offline start --stage local

# API will be available at http://localhost:3001
```

## Step 3: Frontend Setup

### Install Dependencies

```bash
cd ../frontend
npm install
```

### Configure Environment

Create `frontend/.env`:
```bash
VITE_API_URL=http://localhost:3001
VITE_COGNITO_USER_POOL_ID=local-pool-id
VITE_COGNITO_CLIENT_ID=local-client-id
VITE_COGNITO_REGION=us-east-1
```

### Start Development Server

```bash
npm run dev

# Frontend will be available at http://localhost:5173
```

## Step 4: Local Authentication Setup

For local development, you have two options:

### Option 1: Mock Authentication (Recommended)
The backend can run with mocked authentication:

```python
# In backend/src/auth.py, add:
if os.getenv('STAGE') == 'local':
    # Return mock user for local development
    async def get_current_user_id(credentials):
        return "local-test-user"
```

### Option 2: Local Cognito
Set up AWS Cognito User Pool for local testing:

```bash
# Create user pool
aws cognito-idp create-user-pool --pool-name civicforge-local

# Create app client
aws cognito-idp create-user-pool-client \
  --user-pool-id YOUR_POOL_ID \
  --client-name civicforge-local-client
```

## Step 5: Run Tests

### Backend Tests
```bash
cd backend
python -m pytest -v

# With coverage
python -m pytest --cov=src --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## Step 6: Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Backend code in `backend/src/`
- Frontend code in `frontend/src/`
- Tests in `*/tests/` directories

### 3. Run Tests
```bash
# Run both backend and frontend tests
npm test  # From root directory
```

### 4. Check Code Quality
```bash
# Backend
cd backend
black src tests  # Format code
flake8 src tests  # Lint code

# Frontend
cd frontend
npm run lint
npm run format
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

## Troubleshooting

### Port Conflicts
- Backend API: Change port in `serverless.yml` (`custom.serverless-offline.httpPort`)
- Frontend: Change port with `npm run dev -- --port 3000`
- DynamoDB: Use different port with `-p 8001:8000`

### Module Import Errors
- Ensure virtual environment is activated
- Check PYTHONPATH includes backend directory
- Verify all dependencies installed

### CORS Issues
- Backend should allow `http://localhost:5173` in development
- Check `backend/src/app_factory.py` CORS configuration

### Authentication Issues
- For local dev, use mock authentication
- Ensure environment variables are set correctly
- Check Cognito configuration if using real auth

## Next Steps

1. Read the [Architecture Guide](../reference/architecture.md)
2. Review [Contributing Guidelines](../../CONTRIBUTING.md)
3. Check out [Testing Guide](../TESTING.md)
4. Join our Discord for help and discussions

Happy coding! 🚀