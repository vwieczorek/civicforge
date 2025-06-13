# Testing Guidelines for CivicForge Backend

## ⚠️ CRITICAL: Avoid the "Over-Mocking" Trap

**PROBLEM:** Mocking too many dependencies prevents actual code execution, leading to 0% test coverage for critical modules like `routes.py`, `auth.py`, and `db.py`.

**SOLUTION:** Use real implementations with test doubles only where necessary.

## Testing Strategy Hierarchy

### 1. Integration Tests (Highest Priority for Coverage)
**Use for:** API endpoints, full request/response cycles
**Tools:** FastAPI TestClient + moto + dependency injection
**Coverage Impact:** ⭐⭐⭐⭐⭐ (Covers routes.py, auth.py, db.py simultaneously)

```python
# ✅ CORRECT: Integration test with real code execution
@pytest.fixture
def mock_dynamodb_tables():
    with mock_dynamodb():
        # Create real DynamoDB tables using moto
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        # ... table creation code

def test_create_quest_integration(mock_dynamodb_tables, client):
    # Override only auth dependency, let everything else run
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"
    
    response = client.post("/api/v1/quests", json=quest_data)
    # This executes: routes.py → auth.py → db.py → models.py
```

```python
# ❌ WRONG: Over-mocking prevents code execution
@patch('src.routes.db_client', new_callable=AsyncMock)
def test_create_quest_mocked(mock_db, client):
    response = client.post("/api/v1/quests", json=quest_data)
    # This only executes routes.py, db.py gets 0% coverage
```

### 2. Unit Tests (For Complex Business Logic)
**Use for:** State machines, algorithms, pure functions
**Tools:** Direct function calls with minimal mocking
**Coverage Impact:** ⭐⭐⭐ (Targeted coverage of specific modules)

```python
# ✅ CORRECT: Testing business logic without external dependencies
def test_state_machine_validation():
    quest = Quest(questId="q1", creatorId="user1", status=QuestStatus.OPEN)
    assert QuestStateMachine.can_user_claim(quest, "user2") is True
    assert QuestStateMachine.can_user_claim(quest, "user1") is False  # Creator can't claim own quest
```

### 3. Component Tests (For Isolated Components)
**Use for:** Database operations, auth functions, feature flags
**Tools:** Real implementations with test doubles for external services
**Coverage Impact:** ⭐⭐⭐⭐ (High coverage for specific components)

```python
# ✅ CORRECT: Testing database with real DynamoDB (via moto)
async def test_create_user_db(mock_dynamodb_tables):
    db_client = DynamoDBClient()  # Real implementation
    user = User(userId="test", email="test@example.com", ...)
    await db_client.create_user(user)
    # Tests actual serialization, DynamoDB calls, error handling
```

## What to Mock vs. What NOT to Mock

### ✅ DO Mock (External Services):
- **AWS Services in Production:** Use `moto` for DynamoDB, S3, etc.
- **HTTP Requests:** Use `httpx` mocking for external APIs
- **Time/Randomness:** Mock `datetime.utcnow()`, `uuid.uuid4()`
- **Environment Variables:** Use `patch.dict('os.environ')`

### ❌ DON'T Mock (Internal Application Code):
- **Database Clients:** Use moto instead of mocking `db_client`
- **Route Handlers:** Use TestClient instead of mocking endpoints
- **Business Logic:** Test actual state machines, validators, etc.
- **Model Classes:** Test real Pydantic models and their validation

## Coverage-Driven Test Planning

### Phase 1: Foundation (Target: 40% coverage)
1. **Set up integration test infrastructure** (moto, TestClient, fixtures)
2. **Write one "happy path" test per major API endpoint**
3. **Add basic unit tests for pure business logic**

### Phase 2: Error Handling (Target: 60% coverage)
1. **Add error scenarios for each endpoint** (404, 403, 409, etc.)
2. **Test edge cases in business logic**
3. **Test database error conditions**

### Phase 3: Completeness (Target: 70%+ coverage)
1. **Add complex integration scenarios** (full quest lifecycle)
2. **Test authentication edge cases**
3. **Cover remaining utility functions**

## Test File Organization

```
tests/
├── conftest.py                    # Shared fixtures (moto, TestClient)
├── test_api_integration.py        # All API endpoint tests
├── test_business_logic.py         # State machine, validation logic
├── test_database.py              # Database operation edge cases
└── test_auth.py                  # Authentication-specific tests
```

## Quick Coverage Check Commands

```bash
# Run tests with coverage report
pytest --cov=src --cov-report=term-missing

# Run only integration tests (should give highest coverage boost)
pytest tests/test_api_integration.py --cov=src

# Check if you're hitting the 70% threshold
pytest --cov=src --cov-fail-under=70
```

## Red Flags: Signs You're Over-Mocking

1. **0% coverage on routes.py** → You're mocking the database layer
2. **0% coverage on auth.py** → You're mocking authentication
3. **Low coverage on db.py** → You're mocking database operations
4. **Tests pass but coverage is low** → You're testing mocks, not real code

## Example: Before and After

### ❌ Before (Over-Mocked)
```python
@patch('src.routes.db_client', new_callable=AsyncMock)
@patch('src.routes.get_current_user_id', return_value="user123")
def test_create_quest(mock_auth, mock_db, client):
    mock_db.deduct_quest_creation_points.return_value = True
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 201
# Result: Only routes.py gets coverage, auth.py and db.py get 0%
```

### ✅ After (Integration Test)
```python
def test_create_quest_integration(mock_dynamodb_tables, client):
    app.dependency_overrides[get_current_user_id] = lambda: "user123"
    response = client.post("/api/v1/quests", json=quest_data)
    assert response.status_code == 201
# Result: routes.py, auth.py, db.py, models.py all get coverage
```

## Automated Checks

Add to CI/CD pipeline:
```yaml
# .github/workflows/test.yml
- name: Test with coverage
  run: |
    pytest --cov=src --cov-fail-under=70 --cov-report=term-missing
    # Fail if any critical module has 0% coverage
    python scripts/check_zero_coverage.py
```

## Remember: Test Behavior, Not Implementation

**Good Test:** "When I create a quest, it should be stored in the database and returned with a generated ID"

**Bad Test:** "When I call create_quest, db_client.put_item should be called with specific parameters"

The first test exercises real code paths and catches real bugs. The second only tests that you're calling mocks correctly.