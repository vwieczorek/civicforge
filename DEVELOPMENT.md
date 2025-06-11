# Development Guide

## Prerequisites

- Node.js v18+
- Python 3.9+
- AWS CLI configured with credentials
- Docker (for local DynamoDB)

## Frontend Dependencies

The frontend requires `ethers` (v6.9.0+) for cryptographic signature functionality:
```bash
cd frontend
npm install ethers@^6.9.0
```

## Setup

1. **Clone and install dependencies:**
```bash
git clone https://github.com/civicforge/civicforge-serverless
cd civicforge-serverless
npm install
```

2. **Install backend dependencies:**
```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio
cd ..
```

3. **Configure environment:**
```bash
# For frontend
cp frontend/.env.example frontend/.env
# Edit frontend/.env with your Cognito configuration

# Backend uses serverless.yml environment config
```

4. **Start local DynamoDB (optional):**
```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

5. **Run development servers:**
```bash
npm run dev
# Backend: http://localhost:3000/dev
# Frontend: http://localhost:5173
```

## Development Notes

✅ **Core implementation completed:**
- Async/await implementation with aiobotocore
- JWT key rotation handling with TTL cache
- Atomic DynamoDB operations with proper Set handling
- Centralized state machine logic for authorization
- Secure CloudFront deployment infrastructure
- Environment variable management with Vite
- XSS protection with bleach sanitization
- User onboarding with PostConfirmation trigger
- Feature flag system for safe rollouts
- API error monitoring with CloudWatch alarms

🚧 **Remaining for production readiness:**
- Test coverage: Backend 55% → 70%, Frontend 7% → 40%
- Fix failing integration tests
- Frontend testing setup with MSW

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

### Test Coverage Status
**Current Backend Coverage: 55%** (Target: 70%)
**Current Frontend Coverage: 7%** (Target: 40%)

✅ **Excellent Coverage:**
- `signature.py`: 100%
- `state_machine.py`: 99% 
- `models.py`: 98%
- `feature_flags.py`: 94%
- `auth.py`: 79%

🚧 **Needs Improvement:**
- `routes.py`: 33% (integration tests helping)
- `db.py`: 33% (atomic operations tested)

```bash
# Run tests with coverage
cd backend
pytest --cov=src --cov-report=term-missing

# Check for over-mocking issues
python scripts/check_zero_coverage.py
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
│   ├── signature.py  # Cryptographic verification
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

## Security Features

### Atomic Operations
All critical operations use DynamoDB atomic updates to prevent race conditions:
- Attestation additions use conditional expressions
- Quest completion is atomic to prevent double rewards
- User reward updates use atomic ADD operations

### Cryptographic Signatures
- Ethereum wallet signatures for attestations
- Standardized message format between frontend and backend
- Optional feature - users can attest with or without signatures

### Authentication & Authorization
- JWT-based authentication via AWS Cognito
- Role-based access control for quest operations
- State machine validation for all transitions

## API Endpoints

### Quest Management
- `POST /api/v1/quests` - Create a new quest
- `GET /api/v1/quests/{quest_id}` - Get quest details
- `POST /api/v1/quests/{quest_id}/claim` - Claim an open quest
- `POST /api/v1/quests/{quest_id}/submit` - Submit completed work
- `POST /api/v1/quests/{quest_id}/attest` - Attest to completion
- `POST /api/v1/quests/{quest_id}/dispute` - Initiate dispute

### User Management
- `PUT /api/v1/users/wallet` - Update wallet address for signatures

## Deployment

### Development
```bash
npm run deploy:dev
```

### Production
Production deployments happen automatically when PRs are merged to `main`.

Manual deployment (emergency only):
```bash
npm run deploy:prod
```

## Security Scanning

Security scans run automatically in CI/CD:
- Python dependencies: pip-audit
- Node dependencies: npm audit
- Container scanning: Trivy

Manual security check:
```bash
cd backend && pip-audit -r requirements.txt
cd frontend && npm audit
```

## Deployment Status

### Current Status: Development Ready
Core architecture complete. Test coverage at 55%, targeting 70% for production.

### Critical Tasks for Production
- **Test Coverage**: Backend 55% → 70%, Frontend 7% → 40%
- **Fix Integration Tests**: Currently failing due to mocking issues
- **Frontend Testing**: Setup MSW and component tests