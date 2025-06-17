# Testing Strategy

> ⚠️ **DEPRECATED**: This document has been superseded by [docs/TESTING.md](/docs/TESTING.md). Please refer to that document for the current testing strategy and guidelines.

*Last Updated: December 2024*

## Overview

CivicForge maintains high code quality through comprehensive testing at multiple levels. This document outlines our testing philosophy, tools, patterns, and current status.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Testing Levels](#testing-levels)
3. [Backend Testing](#backend-testing)
4. [Frontend Testing](#frontend-testing)
5. [E2E Testing](#e2e-testing)
6. [Coverage Requirements](#coverage-requirements)
7. [Current Status](#current-status)
8. [Testing Tools](#testing-tools)
9. [Best Practices](#best-practices)

## Testing Philosophy

### Core Principles

1. **Test Behavior, Not Implementation**: Focus on what the code does, not how
2. **Fast Feedback**: Unit tests should run in seconds, integration in minutes
3. **Isolation**: Tests should not depend on external services or other tests
4. **Clarity**: Test names should clearly describe what they verify
5. **Maintainability**: Tests should be easy to update as code evolves

### Testing Pyramid

```
         /\
        /E2E\        (5%) - Critical user journeys
       /------\
      /Integration\  (25%) - API and component integration
     /------------\
    /   Unit Tests  \ (70%) - Business logic and utilities
   /----------------\
```

## Testing Levels

### Unit Tests
- **Scope**: Individual functions, methods, and components
- **Speed**: < 100ms per test
- **Dependencies**: Mocked
- **Coverage Target**: 80%+

### Integration Tests
- **Scope**: Multiple components working together
- **Speed**: < 1s per test
- **Dependencies**: Some real, some mocked
- **Coverage Target**: Key workflows

### E2E Tests
- **Scope**: Complete user journeys
- **Speed**: < 30s per test
- **Dependencies**: Real services (staging)
- **Coverage Target**: Critical paths

## Backend Testing

### Test Structure

```python
# test_quest_operations.py
class TestQuestOperations:
    """Test suite for quest CRUD operations"""
    
    def test_create_quest_success(self, authenticated_user, db_session):
        """Should create quest with valid data"""
        # Arrange
        quest_data = create_quest_data()
        
        # Act
        response = create_quest(quest_data, authenticated_user)
        
        # Assert
        assert response.status_code == 201
        assert response.json()["questId"] is not None
```

### Key Testing Patterns

#### 1. Fixtures for Common Setup
```python
@pytest.fixture
def authenticated_user():
    """Provides authenticated user context"""
    return {
        "userId": "test-user-123",
        "username": "testuser",
        "claims": {...}
    }
```

#### 2. Mocking AWS Services
```python
@mock_dynamodb
def test_database_operations():
    """Test with mocked DynamoDB"""
    table = create_test_table()
    # Test operations...
```

#### 3. Parameterized Tests
```python
@pytest.mark.parametrize("status,expected", [
    ("OPEN", True),
    ("CLAIMED", False),
    ("COMPLETE", False),
])
def test_can_claim_quest(status, expected):
    quest = Quest(status=status)
    assert quest.can_claim() == expected
```

### Coverage Areas

- **API Handlers**: All Lambda functions (85% coverage)
- **Business Logic**: Quest state machine, validation rules
- **Data Access**: DynamoDB operations with moto
- **Authentication**: JWT validation, permissions
- **Error Handling**: Edge cases and failure modes

## Frontend Testing

### Test Structure

```typescript
// QuestList.test.tsx
describe('QuestList', () => {
  it('renders quest cards for each quest', async () => {
    // Arrange
    const mockQuests = createMockQuests(3);
    server.use(mockQuestListHandler(mockQuests));
    
    // Act
    render(<QuestList />);
    
    // Assert
    await waitFor(() => {
      mockQuests.forEach(quest => {
        expect(screen.getByText(quest.title)).toBeInTheDocument();
      });
    });
  });
});
```

### Key Testing Patterns

#### 1. Mock Service Worker (MSW)
```typescript
// mocks/handlers.ts
export const handlers = [
  http.get('/api/v1/quests', () => {
    return HttpResponse.json(mockQuestList);
  }),
];
```

#### 2. Testing Hooks
```typescript
// useAuth.test.ts
describe('useAuth', () => {
  it('returns user data when authenticated', () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.user).toBeDefined();
  });
});
```

#### 3. Component Testing
```typescript
// QuestForm.test.tsx
it('validates required fields', async () => {
  const user = userEvent.setup();
  render(<CreateQuest />);
  
  await user.click(screen.getByRole('button', { name: /create/i }));
  
  expect(screen.getByText(/title is required/i)).toBeInTheDocument();
});
```

### Coverage Areas

- **Components**: All UI components (Target: 80%)
- **Hooks**: Custom React hooks
- **API Client**: Request/response handling
- **State Management**: Context and local state
- **User Interactions**: Form submissions, navigation

## E2E Testing

### Test Structure

```typescript
// e2e/quest-lifecycle.spec.ts
test('complete quest lifecycle', async ({ page, authenticatedUser }) => {
  // Create quest
  await page.goto('/create-quest');
  await page.fill('[name="title"]', 'Test Quest');
  await page.fill('[name="description"]', 'Test description');
  await page.click('button[type="submit"]');
  
  // Verify creation
  await expect(page).toHaveURL(/\/quests\/quest-/);
  await expect(page.locator('h1')).toContainText('Test Quest');
});
```

### Key Scenarios

1. **Quest Creation Flow**
   - Login → Create → Verify

2. **Quest Completion Flow**
   - Browse → Claim → Submit → Attestation

3. **Error Handling**
   - Network failures
   - Validation errors
   - Permission denied

## Coverage Requirements

### Targets by Component

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Backend API | 85.78% | 85% | ✅ Achieved |
| Frontend Components | 71.17% | 70% | ✅ Achieved |
| E2E Tests | 0% | 70% | 🚧 High |
| Integration Tests | 75% | 80% | 🚧 Medium |

### Critical Path Coverage

These paths MUST have 100% coverage:

1. **Authentication Flow**
   - Login/logout
   - Token refresh
   - Permission checks

2. **Quest State Transitions**
   - OPEN → CLAIMED
   - CLAIMED → PENDING_REVIEW
   - PENDING_REVIEW → COMPLETE

3. **Reward Distribution**
   - XP calculation
   - Reputation updates
   - Failure handling

## Current Status

### Backend (✅ 85.78% Coverage)

**Well Tested:**
- Quest CRUD operations
- State machine transitions
- Authentication/authorization
- Error handling

**Needs Improvement:**
- Edge cases in reward distribution
- Complex query scenarios

### Frontend (✅ 71.17% Coverage)

**Well Tested:**
- API client
- Authentication hooks
- Core components
- Error boundaries
- Configuration management

**Needs Improvement:**
- Complex user interaction flows
- Advanced form validations
- Edge case scenarios

### E2E (❌ 0% Coverage - Configuration Broken)

**Status:**
- Playwright configuration needs fixing
- Tests exist but cannot run
- Priority for post-MVP

**Planned Coverage:**
- Happy path flows
- Error scenarios
- Network failure handling
- Cross-browser testing

## Testing Tools

### Backend
- **Test Runner**: pytest
- **Mocking**: moto (AWS), unittest.mock
- **Fixtures**: pytest fixtures
- **Coverage**: coverage.py

### Frontend
- **Test Runner**: Vitest
- **Testing Library**: React Testing Library
- **Mocking**: MSW (Mock Service Worker)
- **E2E**: Playwright
- **Coverage**: c8/istanbul

### CI/CD Integration
```yaml
# GitHub Actions
test:
  runs-on: ubuntu-latest
  steps:
    - name: Backend Tests
      run: |
        cd backend
        pytest --cov=src --cov-report=xml
    
    - name: Frontend Tests
      run: |
        cd frontend
        npm test -- --coverage
    
    - name: E2E Tests
      run: |
        cd frontend
        npm run test:e2e
```

## Best Practices

### Writing Good Tests

1. **Descriptive Names**
   ```typescript
   // ❌ Bad
   it('test1', () => {});
   
   // ✅ Good
   it('displays error message when quest creation fails', () => {});
   ```

2. **Arrange-Act-Assert**
   ```python
   def test_claim_quest():
       # Arrange
       quest = create_open_quest()
       user = create_user()
       
       # Act
       result = claim_quest(quest.id, user.id)
       
       # Assert
       assert result.status == "CLAIMED"
       assert result.performer_id == user.id
   ```

3. **Independent Tests**
   - No shared state between tests
   - Can run in any order
   - Clean up after themselves

4. **Focused Tests**
   - One concept per test
   - Clear failure messages
   - Easy to debug

### Maintaining Tests

1. **Update tests when changing code**
2. **Remove obsolete tests**
3. **Refactor test utilities**
4. **Monitor test performance**
5. **Review flaky tests**

## Continuous Improvement

### Monthly Review
- Coverage trends
- Test execution time
- Flaky test analysis
- Missing test scenarios

### Quarterly Goals
- Increase coverage by 5%
- Reduce test time by 10%
- Add new E2E scenarios
- Update test documentation

## Resources

- [Testing Library Docs](https://testing-library.com/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [MSW Documentation](https://mswjs.io/)
- [Playwright Guides](https://playwright.dev/)