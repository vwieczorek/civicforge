# Testing in CivicForge

This guide is the single source of truth for testing philosophy, setup, and best practices for the CivicForge project. It covers backend (Python/pytest), frontend (TypeScript/Vitest), and end-to-end (Playwright) testing.

## 1. Philosophy and Strategy

Our testing strategy is designed to build confidence in our application's behavior, ensure maintainability, and provide fast feedback to developers.

### Core Principles
- **Test Behavior, Not Implementation**: We focus on what the code does from a user's perspective, not the internal implementation details. This makes tests more resilient to refactoring.
- **Prefer Integration Tests**: We favor integration tests that verify multiple components working together. This is enabled by our use of Dependency Injection in the backend and MSW in the frontend. While unit tests are valuable for complex, isolated business logic, most of our confidence comes from tests that mirror real-world usage.
- **Fast & Reliable Feedback**: Tests must be fast and deterministic. We mock external dependencies (like AWS services and third-party APIs) to ensure tests are isolated and run quickly in any environment.
- **Clarity and Maintainability**: Tests are first-class citizens of the codebase. They should be clearly named, easy to read, and structured logically using the Arrange-Act-Assert pattern.

## 2. Test Organization

Our test structure is organized by domain (backend/frontend) and mirrors the source code structure.

### Backend Structure (`backend/tests/`)

We recently refactored our backend tests to improve clarity and focus. The previous monolithic `test_unit.py` and `test_api_basic.py` files have been replaced by a more granular structure. This change, along with the adoption of **dependency injection**, allows for more realistic integration tests with minimal mocking.

```
backend/tests/
├── test_api_integration.py     # API endpoint integration tests
├── test_auth.py                # Authentication and authorization tests
├── test_db_*.py               # Database operation tests
├── test_models_*.py           # Domain model tests
├── test_state_machine_*.py    # Business logic state tests
├── test_user_trigger.py       # Lambda trigger tests
├── test_reprocess_*.py        # Background job tests
└── conftest.py                # Shared pytest fixtures (moto server, db clients)
```

### Frontend Structure (`frontend/src/`)

Frontend tests are co-located with the code they test, following standard practice for React applications.

```
frontend/src/
├── components/
│   └── __tests__/              # Component-level unit and integration tests
├── views/
│   └── __tests__/              # Page-level integration tests
├── api/
│   └── __tests__/              # API client tests
├── test/
│   ├── setup.ts                # Global test setup (e.g., mocking third-party libs)
│   └── mocks/                  # Shared MSW handlers and mock data
```

## 3. How to Run Tests

All test suites can be run via `npm` scripts from their respective `backend` or `frontend` directories.

### Backend Tests

```bash
# Navigate to the backend directory
cd backend

# Run all tests
npm test

# Run all tests and generate a coverage report
npm run test:coverage

# Run a specific test file with verbose output
pytest tests/test_api_integration.py -v

# Run tests matching a pattern
pytest -k "test_create_quest" -v
```

### Frontend Tests

```bash
# Navigate to the frontend directory
cd frontend

# Run all tests in watch mode
npm test

# Run all tests once and generate a coverage report
npm test -- --run --coverage

# Run tests in a specific file
npm test src/views/__tests__/QuestDetail.test.tsx
```

### E2E Tests (Playwright)

**Status**: ✅ Fixed (January 2025).
The Playwright tests have been updated to work with our custom authentication flow.

```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# Run in headed mode to watch the browser
npm run test:e2e -- --headed

# Run a specific test file
npm run test:e2e e2e/quest-interaction.spec.ts
```

## 4. Writing Tests: Best Practices & Patterns

### General Principles

- **Arrange-Act-Assert**: Structure every test clearly.
- **Descriptive Names**: `it('should disable the submit button when the form is invalid')`.
- **Isolate Tests**: Tests must not depend on each other or share state. Use setup/teardown functions to ensure a clean slate for every test.

### Backend Best Practices

#### Prefer Integration Tests with Minimal Mocking
Our primary goal is to test how our code integrates with real dependencies. We use `moto` to create a mocked AWS environment, allowing our handlers and services to run against a realistic in-memory DynamoDB instance. Avoid mocking our own application code.

```python
# ✅ Good: An integration test using dependency injection
async def test_create_quest_integration(authenticated_client):
    # Arrange: authenticated_client uses a real FastAPI app with mocked AWS
    quest_data = {
        "title": "Test Quest",
        "description": "A test quest",
        "rewardXp": 100,
        "rewardReputation": 10
    }
    
    # Act
    response = authenticated_client.post("/api/v1/quests", json=quest_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["title"] == "Test Quest"
    # The quest is actually created in the mocked DynamoDB

# ❌ Bad: Over-mocking our own code
@patch('src.routers.quests_create.get_db_client')
def test_create_quest_handler_calls_service(mock_db):
    # This only tests that a function was called, not what it does
    # We lose confidence that the service and handler work together
```

#### Use Pytest Fixtures for Setup
Use `conftest.py` to define reusable fixtures for setting up authenticated users, database tables, and service instances.

### Frontend Best Practices

#### Test from the User's Perspective
Use `React Testing Library` to query for elements the way a user would (by role, text, or label). Avoid testing implementation details like internal component state.

#### Mock at the Network Boundary
Use **MSW (Mock Service Worker)** to intercept and mock API requests. This ensures our components are tested against realistic API contracts without needing a running backend.

#### Handle Async Operations
Always use `await` with `waitFor` or `findBy*` queries when asserting on UI that appears after an asynchronous event (like an API call).

#### Mock Third-Party Libraries
For libraries that rely on external context (e.g., `react-hot-toast`, `react-router`), provide a global mock in `frontend/src/test/setup.ts` to ensure they work correctly in the test environment.

## 5. Test Coverage

We aim for high coverage on critical business logic and user flows, not just a high overall percentage.

### Coverage Goals

| Component           | Target | Priority |
|---------------------|--------|----------|
| Backend API         | 70%    | High     |
| Frontend Components | 70%    | Medium   |
| E2E Critical Paths  | 100%   | High     |

### Current Status (January 2025)
- **Backend**: 83.60% coverage ✅
- **Frontend**: 71.17% coverage ✅
- **E2E**: Tests fixed and running ✅

### Checking Coverage Locally
Run `npm run test:coverage` in either the `backend` or `frontend` directory. An HTML report will be generated in the `htmlcov/` or `coverage/` directory, respectively.

## 6. Debugging and CI/CD

### Debugging Failed Tests
1. **Isolate the Test**: Use `it.only` (Vitest) or `pytest -k "test_name"` to run a single failing test.
2. **Inspect the Output**: Use `screen.debug()` in the frontend to see the current DOM, or `print()` statements in the backend.
3. **Check Mocks**: Verify that API requests are being intercepted correctly by MSW or that your `moto` setup is complete.
4. **Backend Moto Issues**: If you suspect a stale `moto_server` process, you can kill it with `pkill -f moto_server`.

### CI/CD Integration
Tests are run automatically via GitHub Actions on every pull request. The workflow will fail if tests fail or if coverage drops below the defined thresholds.

```yaml
# .github/workflows/ci.yml
- name: Run Backend Tests & Check Coverage
  run: |
    cd backend
    npm run test:coverage

- name: Run Frontend Tests & Check Coverage
  run: |
    cd frontend
    npm test -- --run --coverage
```

## 7. Recent Improvements (January 2025)

### Backend Testing Infrastructure
- **Dependency Injection**: Migrated from global `db_client` singleton to dependency injection using FastAPI's `Depends()` pattern
- **Removed Over-Mocked Tests**: Deleted `test_api_basic.py` and `test_unit.py` in favor of integration tests
- **Improved Test Organization**: Consolidated tests by domain rather than arbitrary unit/integration split

### Frontend Testing
- **Fixed E2E Tests**: Updated Playwright authentication to work with custom JWT flow instead of AWS Amplify UI
- **Improved Mock Service Worker Setup**: Enhanced MSW handlers for more realistic API responses

## 8. Resources
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [pytest Documentation](https://docs.pytest.org/)
- [MSW Documentation](https://mswjs.io/)
- [Moto Documentation](https://docs.getmoto.org/)