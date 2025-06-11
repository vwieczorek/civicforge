# CivicForge Development Notes

## Testing Strategy

### Testing Architecture

1. **Integration Tests**: Use `TestClient` + `moto server mode` for testing async DynamoDB operations
2. **Unit Tests**: Mock external dependencies for testing business logic in isolation
3. **Moto Server Mode**: Solves aiobotocore compatibility issues by using real HTTP connections

### Key Testing Patterns

```python
# Integration test with moto server
@pytest.mark.asyncio
async def test_api_endpoint(authenticated_client, dynamodb_tables):
    os.environ['DYNAMODB_ENDPOINT_URL'] = dynamodb_tables
    client = authenticated_client('creator_id')
    response = client.post("/api/v1/endpoint", json=data)
```

Use the `authenticated_client` fixture from `conftest.py` for consistent authentication.

### Coverage Requirements

- **Backend**: 70% minimum (currently at 35.39%)
- **Frontend**: 40% minimum (currently at 7%)
- **Enforced by**: pytest.ini configuration

### Quick Commands

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_api_integration.py -v

# Check coverage for critical modules
python scripts/check_zero_coverage.py
```

## Current Architecture

### Backend (Python/FastAPI)
- **FastAPI** with async/await for high performance
- **DynamoDB** for persistence with atomic operations
- **AWS Cognito** for authentication with JWT verification
- **Serverless Framework** for infrastructure as code

### Frontend (React/TypeScript)
- **React 18** with modern hooks
- **Vite** for fast development and building
- **TypeScript** for type safety

### Key Features Implemented
- ✅ Dual-attestation quest system with state machine
- ✅ Cryptographic signature verification  
- ✅ XSS Protection with bleach sanitization
- ✅ User onboarding with PostConfirmation Lambda trigger
- ✅ Feature flags for safe rollouts
- ✅ CloudWatch monitoring and alarms
- ✅ Failed reward retry mechanism with DLQ

## Development Workflow

1. **Make changes** to backend or frontend
2. **Run tests** with coverage: `pytest --cov=src`
3. **Check coverage quality**: `python scripts/check_zero_coverage.py`
4. **Run linting**: `npm run lint` (if available)
5. **Commit changes** when explicitly requested by user

## MVP Deployment Status

### Current Blockers
- **Backend Coverage**: 35.39% / 70% required
- **Frontend Coverage**: 7% / 40% required

### Ready Components
- ✅ Security (XSS protection, JWT auth, atomic operations)
- ✅ Infrastructure (Serverless, CloudWatch, IAM)
- ✅ Core functionality (quest system, state machine, feature flags)

## Project Structure

```
civicforge/
├── backend/               # Python FastAPI backend
│   ├── src/              # Source code
│   │   └── triggers/     # Lambda triggers (PostConfirmation)
│   ├── tests/            # Test files
│   ├── scripts/          # Utility scripts
│   └── serverless.yml    # Infrastructure definition
├── frontend/             # React frontend
│   ├── src/              # Source code  
│   └── package.json      # Dependencies
├── frontend-infra/       # Frontend infrastructure
└── scripts/              # Deployment scripts
```

## Important Files

- `backend/tests/conftest.py` - Test fixtures including moto server setup
- `backend/pytest.ini` - Test configuration with coverage requirements
- `backend/serverless.yml` - Infrastructure as code
- `DEPLOYMENT_STATUS.md` - Detailed deployment checklist