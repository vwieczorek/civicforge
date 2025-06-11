# Development Guide

## Prerequisites

- Node.js v18+
- Python 3.9+
- AWS CLI configured with credentials
- Docker (for local DynamoDB)

## Setup

1. **Clone and install dependencies:**
```bash
git clone https://github.com/civicforge/civicforge-serverless
cd civicforge-serverless
npm install
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration:
# - COGNITO_USER_POOL_ID
# - COGNITO_APP_CLIENT_ID
# - USERS_TABLE
# - QUESTS_TABLE
```

3. **Start local DynamoDB:**
```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

4. **Run development servers:**
```bash
npm run dev
# Backend: http://localhost:3001
# Frontend: http://localhost:3000
```

## Testing

### Unit Tests
```bash
npm run test
```

### Integration Tests
```bash
# Start local services first
npm run dev
# In another terminal
npm run test:integration
```

## Code Style

We use:
- Black for Python formatting
- ESLint + Prettier for TypeScript

```bash
# Format all code
npm run format

# Check linting
npm run lint
```

## Contributing

1. Create an issue describing your change
2. Fork and create a feature branch: `feature/ISSUE-123-brief-description`
3. Make your changes with tests
4. Submit a PR against `main` with:
   - Clear description of the change
   - Link to the issue
   - Test results

## Project Structure

```
backend/
├── src/
│   ├── auth.py       # JWT validation
│   ├── db.py         # DynamoDB operations
│   ├── models.py     # Data models
│   ├── routes.py     # API endpoints
│   └── state_machine.py # Quest transitions
├── handler.py        # Lambda entry point
└── serverless.yml    # Infrastructure config

frontend/
├── src/
│   ├── api/         # Backend client
│   ├── components/  # React components
│   └── pages/       # Page components
└── package.json
```

## Common Tasks

### Add a new API endpoint
1. Add route to `backend/src/routes.py`
2. Add model to `backend/src/models.py` if needed
3. Update API client in `frontend/src/api/client.ts`
4. Add tests

### Update database schema
1. Update models in `backend/src/models.py`
2. Update DynamoDB operations in `backend/src/db.py`
3. Plan for data migration if needed

### Debug Lambda locally
```bash
cd backend
serverless offline --stage dev --debug
```