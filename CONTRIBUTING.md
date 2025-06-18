# Contributing to CivicForge

Welcome to CivicForge! This guide will help you get started with development and contribution.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running Tests](#running-tests)
- [Code Style & Linting](#code-style--linting)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Common Development Tasks](#common-development-tasks)
- [AI-Assisted Development](#ai-assisted-development)
- [Security Considerations](#security-considerations)

## Prerequisites

- Node.js v18+
- Python 3.11+
- AWS CLI configured with credentials
- Docker (optional, for local DynamoDB)

## Local Development Setup

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/civicforge/civicforge-serverless
cd civicforge-serverless
npm install
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
cd ..
```

### 3. Frontend Dependencies

The frontend requires `ethers` for cryptographic signatures:
```bash
cd frontend
npm install
```

### 4. Environment Configuration

```bash
# Frontend environment
cp frontend/.env.example frontend/.env
# Edit frontend/.env with your Cognito configuration

# Backend uses serverless.yml for environment config
```

### 5. Start Development Servers

```bash
# Start both frontend and backend
npm run dev

# Backend API: http://localhost:3001
# Frontend: http://localhost:5173
```

Optional: Run local DynamoDB
```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

## Testing

### Testing Philosophy

We maintain high testing standards to ensure reliability and maintainability:
- **Backend**: 85%+ coverage requirement
- **Frontend**: 70%+ coverage requirement
- Test behavior, not implementation
- Write tests that give confidence in production

For current test metrics, see **[Project Status](./PROJECT_STATUS.md)**.

### Running Tests

```bash
# Run all tests
npm test

# Backend tests
npm run test:backend          # Run all backend tests
npm run test:backend:coverage  # With coverage report
npm run test:backend:watch     # Watch mode

# Frontend tests  
npm run test:frontend          # Run all frontend tests
npm run test:frontend:coverage # With coverage report
npm run test:frontend:watch    # Watch mode

# E2E tests
npm run test:e2e              # Run Playwright E2E tests
npm run test:e2e:ui           # With Playwright UI

# Quality checks
npm run test:coverage          # Full coverage report
npm run lint                   # Run all linters
npm run typecheck             # TypeScript checks
```

### Testing

For detailed guidelines on writing tests, best practices, and coverage requirements, please refer to the dedicated [Testing Documentation](docs/TESTING.md).

### Continuous Integration

All tests run automatically on:
- Pull request creation/update
- Merges to main branch
- Pre-deployment checks

PR checks must pass:
- ✅ All tests passing
- ✅ Coverage thresholds met
- ✅ No linting errors
- ✅ TypeScript compilation successful

## Code Style & Linting

### Python (Backend)
```bash
# Format code
black backend/

# Check linting
ruff check backend/
```

### TypeScript (Frontend)
```bash
# Format and lint
cd frontend
npm run lint
```

## Pull Request Process

1. **Create an Issue**: Describe your proposed change
2. **Fork and Branch**: Create a feature branch `feature/ISSUE-123-brief-description`
3. **Write Tests**: All new features require tests
4. **Update Documentation**: Keep docs in sync with code changes
5. **Submit PR**: Include:
   - Clear description linking to the issue
   - Test results screenshot/output
   - Any breaking changes noted

### PR Requirements
- Backend coverage must remain ≥70%
- New frontend features or components **must** include corresponding unit or integration tests
- PRs modifying critical user flows should include or update E2E tests
- All tests must pass (backend, frontend unit, and E2E)
- Code must be formatted and linted
- TypeScript must compile without errors
- No deployment from feature branches to production

## Project Structure

```
civicforge/
├── backend/                 # Python FastAPI backend
│   ├── handlers/           # Isolated Lambda function handlers
│   │   ├── api.py         # General read operations
│   │   ├── create_quest.py # Quest creation handler
│   │   ├── attest_quest.py # Attestation & rewards
│   │   └── delete_quest.py # Quest deletion
│   ├── src/
│   │   ├── routers/       # FastAPI route definitions
│   │   ├── app_factory.py # Application factory pattern
│   │   ├── auth.py        # JWT validation & Cognito
│   │   ├── db.py          # DynamoDB operations
│   │   ├── models.py      # Pydantic data models
│   │   ├── state_machine.py # Quest state transitions
│   │   └── triggers/      # Event-driven Lambdas
│   ├── tests/             # Comprehensive test suite
│   └── serverless.yml     # Infrastructure as code
│
├── frontend/              # React TypeScript frontend
│   ├── src/
│   │   ├── api/          # Backend API client
│   │   ├── components/   # Reusable React components
│   │   ├── views/        # Page components
│   │   └── config.ts     # Environment configuration
│   └── package.json
│
├── scripts/              # Deployment & utility scripts
│   └── deploy.sh        # Safe deployment with checks
└── docs/                # Documentation
    └── OPERATIONS.md    # Production runbook
```

## Common Development Tasks

For detailed guides on common tasks, see the [How-To Guides](docs/how-to-guides/) section.

### Add a New API Endpoint

For a comprehensive guide, see [How to Add a New API Endpoint](docs/how-to-guides/add-new-api-endpoint.md).

⚠️ **Important**: CivicForge uses a modular Lambda architecture where each endpoint type has its own handler with isolated IAM permissions.

#### Architecture Overview
- Each Lambda handler in `handlers/` creates a FastAPI app via the app factory
- Handlers import specific routers from `src/routers/`
- Each handler has narrowly-scoped IAM permissions (least privilege)

#### Steps to Add an Endpoint

1. **Choose the appropriate router based on operation type**:
   - 📖 Read operations → `src/routers/quests_read.py` or `users.py`
   - ➕ Create operations → `src/routers/quests_create.py`
   - 🔄 Update operations → `src/routers/quests_actions.py`
   - ✅ Attestation → `src/routers/quests_attest.py`
   - 🗑️ Delete operations → `src/routers/quests_delete.py`

2. **Add your route to the chosen router**:
   ```python
   @router.post("/new-endpoint")
   async def new_endpoint(
       request: NewRequest,
       user_id: str = Depends(get_current_user_id),
       db: DynamoDBClient = Depends(get_db_client)
   ):
       # Implementation
   ```

3. **If the router doesn't fit an existing handler, create a new one**:
   - Create `handlers/new_handler.py`:
     ```python
     from src.app_factory import create_app
     from src.routers import new_router
     
     app = create_app(routers=[new_router.router])
     handler = app.handler
     ```
   
   - Update `serverless.yml`:
     ```yaml
     newHandler:
       handler: handlers.new_handler.handler
       events:
         - httpApi:
             path: /api/v1/new-endpoint
             method: POST
       iamRoleStatements:
         - Effect: Allow
           Action:
             - dynamodb:GetItem  # Only what's needed!
           Resource: !GetAtt UsersTable.Arn
     ```

4. **Update the frontend**:
   - Add method to `frontend/src/api/client.ts`
   - Update TypeScript types in `frontend/src/api/types.ts`

5. **Write comprehensive tests**:
   - Backend: Add tests in `backend/tests/test_new_endpoint.py`
   - Frontend: Add component tests using MSW for API mocking

### Update Database Schema

1. Update models in `backend/src/models.py`
2. Modify DynamoDB operations in `backend/src/db.py`
3. Consider data migration strategy for existing data
4. Update any affected Lambda handlers

### Debug Lambda Locally

```bash
cd backend
serverless offline --stage dev --debug
```

### Deploy to Development

```bash
# Uses safety checks even for dev
./scripts/deploy.sh dev
```

## AI-Assisted Development

This project is optimized for development with AI assistants. Here are key patterns:

### Testing Patterns

```python
# Integration test pattern with new handler structure
@pytest.mark.asyncio
async def test_api_endpoint(authenticated_client, dynamodb_tables):
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    client = authenticated_client('creator_id')
    response = client.post("/api/v1/endpoint", json=data)
```

### Mock Pattern for Handler Tests

```python
# Use MockDBClient for isolated handler testing
class MockDBClient:
    def __init__(self):
        self.get_user = AsyncMock()
        self.create_quest = AsyncMock()
        # ... other methods

@pytest.fixture
def mock_db_client():
    mock_client = MockDBClient()
    with patch('src.routers.quests_create.db_client', mock_client):
        yield mock_client
```

### Frontend Component Test Pattern

```typescript
// Example using Vitest, React Testing Library, and MSW
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import QuestList from './QuestList';

describe('QuestList', () => {
  it('displays quests from API', async () => {
    // MSW will intercept this request
    render(<QuestList />);
    
    // Wait for async data to load
    await waitFor(() => {
      expect(screen.getByText('Test Quest')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    // Override handler for this specific test
    server.use(
      http.get('/api/v1/quests', () => {
        return HttpResponse.json({ error: 'Server error' }, { status: 500 });
      })
    );
    
    render(<QuestList />);
    
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
```

### Key Implementation Details

- **Handler Separation**: Each Lambda has its own IAM role
- **Async/Await**: All backend operations use async patterns
- **Atomic Operations**: DynamoDB updates use conditional expressions
- **Idempotency**: Failed rewards use unique IDs to prevent double-processing
- **Lease System**: Prevents concurrent processing of failed rewards
- **CORS**: Explicit headers only, no wildcards

### Important Files for Context

- `backend/handlers/` - Lambda function entry points
- `backend/src/app_factory.py` - FastAPI application factory
- `backend/src/routers/` - Route definitions by domain
- `backend/tests/conftest.py` - Test fixtures and setup
- `backend/serverless.yml` - Infrastructure configuration
- `scripts/deploy.sh` - Deployment with safety checks

## Security Considerations

### Authentication & Authorization
- JWT-based auth via AWS Cognito
- Per-function IAM roles with least privilege
- State machine validates all quest transitions

### Data Protection
- XSS prevention with bleach sanitization
- Input validation on all API endpoints
- Atomic DynamoDB operations prevent race conditions
- Explicit CORS headers (no wildcards)

### Handler Security
Each Lambda function has minimal permissions:
- **API Handler**: Read-only, explicitly denied deletes
- **Create Quest**: Can only create quests and update user points
- **Attest Quest**: Can update quests and distribute rewards
- **Delete Quest**: Can only delete OPEN quests

### Cryptographic Features
- Optional Ethereum wallet signatures for attestations
- Standardized message format between frontend/backend
- Signature verification in `backend/src/signature.py`

### Security Scanning
```bash
# Python dependencies
cd backend && pip-audit

# Node dependencies
cd frontend && npm audit

# Check for secrets
git secrets --scan
```

## Deployment Safety

The deployment script (`scripts/deploy.sh`) includes safety checks:
- ✅ Clean git status required
- ✅ Main branch required for production
- ✅ All tests must pass
- ✅ Manual confirmation for production
- ✅ Post-deployment health checks

## Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: GitHub discussions for questions and ideas
- **Documentation**: Check [docs/](docs/) for comprehensive guides
- **Architecture**: See [Architecture Overview](docs/reference/architecture.md)
- **API Reference**: See [API Documentation](docs/reference/api-reference.md)
- **Security**: See [Security Model](docs/reference/security-model.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details.