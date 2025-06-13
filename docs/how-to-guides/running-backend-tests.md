# How to Run Backend Tests

This guide walks you through running the CivicForge backend test suite.

## Prerequisites

- Python 3.9+
- Virtual environment activated
- Dependencies installed: `pip install -r requirements.txt`

## Running All Tests

```bash
# From the backend directory
cd backend
python -m pytest

# With coverage report
python -m pytest --cov=src --cov-report=html

# With verbose output
python -m pytest -v
```

## Running Specific Test Categories

### Unit Tests
```bash
python -m pytest tests/test_unit.py -v
```

### Integration Tests
```bash
python -m pytest tests/test_api_integration.py -v
```

### Database Tests
```bash
python -m pytest tests/test_db_*.py -v
```

### Authentication Tests
```bash
python -m pytest tests/test_auth.py -v
```

## Test Coverage

The project requires:
- Overall backend coverage: >70%
- Critical paths: 100% coverage

Check current coverage:
```bash
python -m pytest --cov=src --cov-report=term-missing
```

View HTML coverage report:
```bash
python -m pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Running Tests in Watch Mode

For development, use pytest-watch:
```bash
pip install pytest-watch
ptw -- --cov=src
```

## Testing Best Practices

### 1. Avoid Over-Mocking
Use real implementations with test doubles only where necessary:

```python
# ✅ Good: Integration test with real code
@pytest.fixture
def mock_dynamodb_tables():
    with mock_dynamodb():
        # Create real tables
        yield

# ❌ Bad: Over-mocked test
@patch('src.db.DynamoDBClient')
def test_something(mock_db):
    # This doesn't test real behavior
```

### 2. Test Categories

- **Integration Tests**: Full API flows with mocked AWS services
- **Unit Tests**: Isolated business logic
- **Atomic Operation Tests**: Race conditions and concurrency

### 3. Critical Path Coverage

Ensure 100% coverage for:
- Authentication flows
- Atomic database operations
- Reward processing
- State transitions

## Troubleshooting

### Import Errors
- Ensure you're in the backend directory
- Check PYTHONPATH includes the src directory
- Verify all dependencies are installed

### Moto Server Issues
- Kill any existing moto_server processes: `pkill -f moto_server`
- Check port 5000 is available
- Use `@mock_dynamodb` decorator for simpler tests

### Coverage Gaps
- Run with `--cov-report=term-missing` to see uncovered lines
- Focus on integration tests for better coverage
- Check for over-mocked tests that prevent code execution

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Pre-deployment

The CI pipeline will fail if coverage drops below 70%.