# How to Run Frontend Tests

This guide walks you through running the CivicForge frontend test suite.

## Prerequisites

- Node.js 18+
- Dependencies installed: `cd frontend && npm install`

## Running All Tests

```bash
# From the frontend directory
cd frontend

# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run with coverage
npm run coverage
```

## Running Specific Test Types

### Unit Tests
```bash
# Run component tests
npm test -- src/components

# Run view tests
npm test -- src/views
```

### Integration Tests
```bash
# Run API client tests
npm test -- src/api
```

### End-to-End Tests
```bash
# Run Playwright E2E tests
npm run test:e2e

# Run in headed mode (see browser)
npm run test:e2e -- --headed

# Run specific test file
npm run test:e2e quest-interaction
```

## Test Coverage

The project requires:
- Frontend coverage: >70%
- All components tested
- Critical user flows covered

Check current coverage:
```bash
npm run coverage
```

## Writing Tests

### Component Tests
```typescript
// Using React Testing Library
import { render, screen, fireEvent } from '@testing-library/react';
import { CreateQuest } from './CreateQuest';

test('validates required fields', async () => {
  render(<CreateQuest />);
  
  const submitButton = screen.getByRole('button', { name: /create quest/i });
  fireEvent.click(submitButton);
  
  expect(await screen.findByText(/title is required/i)).toBeInTheDocument();
});
```

### API Tests with MSW
```typescript
// Mock API responses
import { rest } from 'msw';
import { server } from '../mocks/server';

test('handles API errors', async () => {
  server.use(
    rest.post('/api/v1/quests', (req, res, ctx) => {
      return res(ctx.status(500), ctx.json({ detail: 'Server error' }));
    })
  );
  
  // Test error handling
});
```

## Testing Best Practices

### 1. Use Testing Library Queries
```typescript
// ✅ Good: Accessible queries
screen.getByRole('button', { name: /submit/i });
screen.getByLabelText(/email/i);

// ❌ Bad: Implementation details
screen.getByClassName('submit-btn');
screen.getByTestId('email-input');
```

### 2. Test User Behavior
```typescript
// ✅ Good: Test what users do
await userEvent.type(screen.getByLabelText(/title/i), 'New Quest');
await userEvent.click(screen.getByRole('button', { name: /create/i }));

// ❌ Bad: Test implementation
expect(component.state.title).toBe('New Quest');
```

### 3. Mock at the Network Level
Use MSW for consistent API mocking across all test types.

## Troubleshooting

### Test Failures
- Check for `act()` warnings - wrap state updates properly
- Ensure async operations complete before assertions
- Use `findBy` queries for elements that appear async

### Coverage Issues
- Current coverage is ~30% (needs 70%)
- Focus on testing user flows, not implementation
- Ensure MSW handlers cover all API calls

### React Router Issues
Tests include MemoryRouter for routing context:
```typescript
render(
  <MemoryRouter initialEntries={['/quest/123']}>
    <QuestDetail />
  </MemoryRouter>
);
```

## CI/CD Integration

Frontend tests run on:
- Pull requests
- Pre-deployment
- Commits to main

The pipeline fails if:
- Any test fails
- Coverage drops below 70%
- Build warnings exist