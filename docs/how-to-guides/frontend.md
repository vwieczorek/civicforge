# CivicForge Testing Standards

## Overview

This document outlines the testing standards and best practices for the CivicForge frontend application.

## Testing Stack

- **Unit/Integration Tests**: Vitest + React Testing Library
- **E2E Tests**: Playwright
- **API Mocking**: Mock Service Worker (MSW)
- **Test Data**: Factory functions with Faker.js

## Network Mocking Standards

### ✅ DO: Use MSW for All API Mocking

This project uses Mock Service Worker (MSW) for all unit and integration tests that require network requests. Manual mocking of `global.fetch` with `vi.fn()` is **strictly forbidden** to ensure test consistency and reliability.

- All handlers are defined in `src/mocks/handlers.ts`
- To override a handler for a specific error case in a single test, use `server.use()`

Example:
```typescript
// ✅ GOOD - Using MSW
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';

test('handles API error', async () => {
  server.use(
    http.get('/api/quests', () => {
      return HttpResponse.json({ error: 'Server error' }, { status: 500 });
    })
  );
  
  // Test error handling
});

// ❌ BAD - Manual fetch mocking
const mockFetch = vi.fn();
global.fetch = mockFetch;
```

### ✅ DO: Use Playwright Route Interception for E2E Edge Cases

For E2E tests, use real backend APIs for critical paths and Playwright's route interception for edge cases:

```typescript
// Mock specific error scenarios
await page.route('**/api/quests/*/claim', route => {
  route.fulfill({
    status: 400,
    body: JSON.stringify({ error: 'Already claimed' })
  });
});
```

## Test Organization

### Unit/Integration Tests (`src/**/__tests__/`)
- Co-located with source files
- Focus on component logic and interactions
- Use MSW for API calls
- Aim for 80%+ coverage on business logic

### E2E Tests (`e2e/`)
- Test critical user journeys
- Use real backend for happy paths
- Mock edge cases and errors
- Run against local dev server

## E2E Testing Best Practices

### 1. Authentication State Management
```typescript
// auth.setup.ts - Run once before all tests
setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  // ... perform login
  await page.context().storageState({ path: 'auth-state.json' });
});
```

### 2. Critical User Journeys
1. **User Login Flow** - Test actual Cognito integration
2. **Quest Discovery** - Browse and filter quests
3. **Quest Interaction** - Claim, submit, view details
4. **Quest Attestation** - Complete dual-attestation process

### 3. Hybrid Testing Approach
- **Real Backend**: Use for core happy paths
- **Mocked Responses**: Use for error states, edge cases
- **Session Persistence**: Reuse auth state across tests

## Running Tests

```bash
# Unit/Integration tests
npm test              # Run in watch mode
npm run coverage      # Generate coverage report

# E2E tests
npm run test:e2e      # Run all E2E tests
npm run test:e2e:ui   # Open Playwright UI mode

# All tests
npm run test:all      # Run unit + E2E tests
```

## Coverage Requirements

- **Overall**: 70% minimum
- **Critical Components**: 80%+ recommended
  - API client
  - Authentication flows
  - Quest interaction components
  - State management

## Test Data Management

### Factory Functions
Use the test data factories for consistent test data:

```typescript
import { createMockQuest, createMockUser } from '../test/mocks/factory';

const testQuest = createMockQuest({
  status: QuestStatus.OPEN,
  rewardAmount: 100
});
```

### E2E Test Data
- Use dedicated test accounts in Cognito
- Create unique test data per test run
- Clean up test data after tests

## Debugging Tests

### Unit Tests
```bash
# Run specific test file
npm test src/components/QuestList.test.tsx

# Debug in VS Code
# Use JavaScript Debug Terminal
```

### E2E Tests
```bash
# Run with UI mode for debugging
npm run test:e2e:ui

# Generate trace on failure
npm run test:e2e -- --trace on

# View trace
npx playwright show-trace trace.zip
```

## Common Patterns

### Testing Error States
```typescript
// Unit test with MSW
server.use(
  http.get('/api/quests', () => {
    return HttpResponse.json({ error: 'Failed' }, { status: 500 });
  })
);

// E2E test with Playwright
await page.route('**/api/quests', route => {
  route.fulfill({ status: 500 });
});
```

### Testing Loading States
```typescript
// Delay response to test loading UI
server.use(
  http.get('/api/quests', async () => {
    await delay(1000);
    return HttpResponse.json(data);
  })
);
```

## Migration Guide

If you encounter tests using manual fetch mocks:

1. Remove `global.fetch = mockFetch`
2. Remove manual mock setup
3. Add MSW handler to `src/mocks/handlers.ts`
4. Update test to use MSW patterns

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Mock Service Worker](https://mswjs.io/)
- [Playwright Documentation](https://playwright.dev/)