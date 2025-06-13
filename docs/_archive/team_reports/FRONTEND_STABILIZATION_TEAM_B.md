# Team B: Frontend Test Stabilization Guide

## Overview

The frontend test suite is in critical condition with 11/14 test files failing. This guide provides a systematic approach to stabilize the testing infrastructure before adding new tests.

## Current State Analysis

### Test Infrastructure Issues
- **React act() warnings**: Async state updates not properly handled
- **Component prop mismatches**: Tests expect different props than components accept
- **Mock configuration errors**: MSW and window.ethereum mocks failing
- **E2E environment broken**: Playwright tests can't start due to env config

### Failure Statistics
- Total test files: 14
- Failed: 11 files (78.5%)
- Failed tests: 30 out of 85 (35.3%)
- Critical path tests: ALL FAILING

## Phase 1: Fix E2E Environment (Day 1)

### 1.1 Diagnose Playwright Configuration

```bash
# Check current E2E setup
cd frontend
npm run test:e2e -- --debug
```

### 1.2 Fix Environment Variables

Create `frontend/e2e/.env.test`:

```env
VITE_API_BASE_URL=http://localhost:3001
VITE_APP_TITLE=CivicForge
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=test-pool-id
VITE_COGNITO_CLIENT_ID=test-client-id
```

### 1.3 Update Playwright Config

Update `frontend/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// Load test environment variables
dotenv.config({ path: path.resolve(__dirname, 'e2e/.env.test') });

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: !process.env.CI,
    env: {
      ...process.env,
      VITE_API_BASE_URL: 'http://localhost:3001',
    },
  },
});
```

### 1.4 Create E2E Test Server Mock

Create `frontend/e2e/setup/test-server.ts`:

```typescript
import { setupServer } from 'msw/node';
import { rest } from 'msw';

export const server = setupServer(
  // Mock auth endpoints
  rest.post('http://localhost:3001/api/v1/auth/login', (req, res, ctx) => {
    return res(ctx.json({ token: 'test-token', userId: 'test-user' }));
  }),
  
  // Mock quest endpoints
  rest.get('http://localhost:3001/api/v1/quests', (req, res, ctx) => {
    return res(ctx.json({ quests: [], total: 0 }));
  }),
);

// Start server before all tests
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Phase 2: Stabilize MSW Mocking (Day 2)

### 2.1 Centralize MSW Handlers

Create `frontend/src/test/mocks/handlers.ts`:

```typescript
import { rest } from 'msw';
import { API_BASE_URL } from '@/config';

// Define the API contract based on Team A's documentation
export const handlers = [
  // Auth handlers
  rest.post(`${API_BASE_URL}/api/v1/auth/login`, async (req, res, ctx) => {
    const { email, password } = await req.json();
    
    if (email === 'test@example.com' && password === 'password') {
      return res(
        ctx.status(200),
        ctx.json({
          token: 'mock-jwt-token',
          userId: 'test-user-123',
          email: 'test@example.com'
        })
      );
    }
    
    return res(
      ctx.status(401),
      ctx.json({ error: 'Invalid credentials' })
    );
  }),

  // Quest creation handler
  rest.post(`${API_BASE_URL}/api/v1/quests`, async (req, res, ctx) => {
    const body = await req.json();
    
    // Validate required fields
    if (!body.title || !body.description) {
      return res(
        ctx.status(400),
        ctx.json({ error: 'Title and description are required' })
      );
    }
    
    return res(
      ctx.status(201),
      ctx.json({
        questId: 'quest-123',
        ...body,
        status: 'ACTIVE',
        createdAt: new Date().toISOString()
      })
    );
  }),

  // Quest attestation handler
  rest.post(`${API_BASE_URL}/api/v1/quests/:questId/attest`, async (req, res, ctx) => {
    const { questId } = req.params;
    const body = await req.json();
    
    // Check for duplicate attestation (403 after security fixes)
    if (body.simulateDuplicate) {
      return res(
        ctx.status(403),
        ctx.json({ error: 'User has already attested to this quest' })
      );
    }
    
    return res(
      ctx.status(200),
      ctx.json({
        questId,
        attestationId: 'attest-123',
        message: 'Attestation recorded successfully'
      })
    );
  }),

  // User profile handler
  rest.get(`${API_BASE_URL}/api/v1/users/:userId`, (req, res, ctx) => {
    const { userId } = req.params;
    
    return res(
      ctx.status(200),
      ctx.json({
        userId,
        username: 'testuser',
        email: 'test@example.com',
        reputation: 100,
        experience: 500,
        questCreationPoints: 10,
        walletAddress: null,
        createdAt: '2024-01-01T00:00:00Z'
      })
    );
  }),
];

// Error simulation handlers for testing error states
export const errorHandlers = [
  rest.post(`${API_BASE_URL}/api/v1/quests`, (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({ error: 'Internal server error' })
    );
  }),
];
```

### 2.2 Update Test Setup

Update `frontend/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll } from 'vitest';
import { server } from './mocks/server';

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

// Reset handlers after each test
afterEach(() => {
  cleanup();
  server.resetHandlers();
});

// Clean up after all tests
afterAll(() => {
  server.close();
});

// Mock window.ethereum for wallet tests
global.window.ethereum = {
  request: vi.fn(),
  on: vi.fn(),
  removeListener: vi.fn(),
};

// Mock Amplify for auth tests
vi.mock('aws-amplify', () => ({
  Auth: {
    currentAuthenticatedUser: vi.fn(),
    signIn: vi.fn(),
    signOut: vi.fn(),
  },
  configure: vi.fn(),
}));
```

## Phase 3: Fix React Act Warnings (Day 2-3)

### 3.1 Common Act Warning Patterns and Fixes

#### Pattern 1: Not awaiting async updates

**Bad:**
```typescript
test('shows user data', () => {
  render(<UserProfile userId="123" />);
  expect(screen.getByText('testuser')).toBeInTheDocument();
});
```

**Good:**
```typescript
test('shows user data', async () => {
  render(<UserProfile userId="123" />);
  
  // Wait for async data to load
  await waitFor(() => {
    expect(screen.getByText('testuser')).toBeInTheDocument();
  });
});
```

#### Pattern 2: Not wrapping state updates

**Bad:**
```typescript
test('submits form', () => {
  render(<CreateQuest />);
  const button = screen.getByRole('button', { name: /create/i });
  
  fireEvent.click(button);
  // State update happens here, causing act warning
});
```

**Good:**
```typescript
test('submits form', async () => {
  const user = userEvent.setup();
  render(<CreateQuest />);
  const button = screen.getByRole('button', { name: /create/i });
  
  await user.click(button);
  // userEvent automatically wraps in act()
});
```

### 3.2 Fix Component Test Files

#### Fix CreateQuest.test.tsx

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { CreateQuest } from '@/views/CreateQuest';
import { server } from '@/test/mocks/server';
import { rest } from 'msw';

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <MemoryRouter>
      {component}
    </MemoryRouter>
  );
};

describe('CreateQuest', () => {
  it('renders form fields', () => {
    renderWithRouter(<CreateQuest />);
    
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create quest/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderWithRouter(<CreateQuest />);
    
    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument();
      expect(screen.getByText(/description is required/i)).toBeInTheDocument();
    });
  });

  it('successfully creates a quest', async () => {
    const user = userEvent.setup();
    const mockNavigate = vi.fn();
    
    // Mock useNavigate
    vi.mock('react-router-dom', async () => {
      const actual = await vi.importActual('react-router-dom');
      return {
        ...actual,
        useNavigate: () => mockNavigate,
      };
    });
    
    renderWithRouter(<CreateQuest />);
    
    // Fill form
    await user.type(screen.getByLabelText(/title/i), 'Test Quest');
    await user.type(screen.getByLabelText(/description/i), 'Test Description');
    await user.type(screen.getByLabelText(/xp reward/i), '100');
    
    // Submit
    await user.click(screen.getByRole('button', { name: /create quest/i }));
    
    // Wait for navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/quests/quest-123');
    });
  });

  it('shows error message on API failure', async () => {
    const user = userEvent.setup();
    
    // Override handler to simulate error
    server.use(
      rest.post('*/api/v1/quests', (req, res, ctx) => {
        return res(
          ctx.status(500),
          ctx.json({ error: 'Server error' })
        );
      })
    );
    
    renderWithRouter(<CreateQuest />);
    
    // Fill and submit form
    await user.type(screen.getByLabelText(/title/i), 'Test Quest');
    await user.type(screen.getByLabelText(/description/i), 'Test Description');
    await user.click(screen.getByRole('button', { name: /create quest/i }));
    
    // Check for error message
    await waitFor(() => {
      expect(screen.getByText(/server error/i)).toBeInTheDocument();
    });
    
    // Verify button is re-enabled
    expect(screen.getByRole('button', { name: /create quest/i })).not.toBeDisabled();
  });
});
```

#### Fix QuestAttestation Component Props

First, check the actual component props:

```typescript
// Update test to match actual component interface
describe('QuestAttestation', () => {
  const defaultProps = {
    questId: 'quest-123',
    questStatus: 'SUBMITTED',
    userRole: 'REQUESTOR',
    onAttestationComplete: vi.fn(),
  };

  it('renders attestation form for requestor', () => {
    render(<QuestAttestation {...defaultProps} />);
    
    expect(screen.getByText(/attest quest completion/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
  });
});
```

## Phase 4: Implement Critical Path E2E Test (Day 4-5)

### 4.1 Create Golden Path E2E Test

Create `frontend/e2e/critical-path.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Critical Path: Quest Creation to Attestation', () => {
  test('complete quest lifecycle', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // 2. Create Quest
    await page.click('text=Create Quest');
    await page.fill('input[name="title"]', 'E2E Test Quest');
    await page.fill('textarea[name="description"]', 'This is an E2E test quest');
    await page.fill('input[name="xpReward"]', '100');
    await page.fill('input[name="reputationReward"]', '50');
    
    await page.click('button:has-text("Create Quest")');
    
    // Wait for quest detail page
    await expect(page).toHaveURL(/\/quests\/quest-/);
    
    // 3. Switch to performer account
    await page.click('text=Logout');
    await page.goto('/login');
    await page.fill('input[name="email"]', 'performer@example.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');
    
    // 4. Claim quest
    await page.goto('/quests');
    await page.click('text=E2E Test Quest');
    await page.click('button:has-text("Claim Quest")');
    
    await expect(page.locator('text=Quest claimed successfully')).toBeVisible();
    
    // 5. Submit quest
    await page.fill('textarea[name="submissionNotes"]', 'Quest completed');
    await page.click('button:has-text("Submit Quest")');
    
    await expect(page.locator('text=Quest submitted')).toBeVisible();
    
    // 6. Performer attestation
    await page.click('button:has-text("Attest Completion")');
    await page.fill('textarea[name="attestationNotes"]', 'I completed this quest');
    await page.click('button:has-text("Confirm Attestation")');
    
    await expect(page.locator('text=Attestation recorded')).toBeVisible();
    
    // 7. Switch back to requestor
    await page.click('text=Logout');
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');
    
    // 8. Requestor attestation
    await page.goto('/quests/quest-123'); // Use actual quest ID
    await page.click('button:has-text("Approve Completion")');
    await page.fill('textarea[name="attestationNotes"]', 'Confirmed completed');
    await page.click('button:has-text("Confirm Attestation")');
    
    // 9. Verify quest completed
    await expect(page.locator('text=Quest Completed')).toBeVisible();
    await expect(page.locator('text=Rewards Distributed')).toBeVisible();
  });
});
```

## Testing Checklist

### Phase 1 (Day 1)
- [ ] E2E environment variables configured
- [ ] Playwright config updated
- [ ] E2E tests can start without errors
- [ ] Basic E2E test runs successfully

### Phase 2 (Day 2)
- [ ] MSW handlers centralized
- [ ] API contract matches Team A documentation
- [ ] Test setup properly initializes mocks
- [ ] Window.ethereum mock working

### Phase 3 (Day 2-3)
- [ ] All act() warnings resolved
- [ ] Component prop mismatches fixed
- [ ] CreateQuest tests passing
- [ ] QuestAttestation tests passing
- [ ] UserProfile tests passing
- [ ] QuestDetail tests passing

### Phase 4 (Day 4-5)
- [ ] Critical path E2E test implemented
- [ ] E2E test covers full attestation flow
- [ ] All critical path component tests passing
- [ ] Test coverage meets quality gates (not quantity)

## Success Criteria

1. **Zero failing tests** in critical path components
2. **E2E test suite functional** and passing
3. **No act() warnings** in test output
4. **Stable mock layer** that reflects actual API behavior
5. **Clear documentation** of API contract for ongoing maintenance

## Rollback Plan

If stabilization efforts fail:

1. **Document all blocking issues** with reproducible examples
2. **Escalate to Team C** for infrastructure support
3. **Consider alternative testing strategies** (e.g., manual testing protocol)
4. **Implement feature flags** to safely deploy without full test coverage

## Next Steps After Stabilization

Once the test infrastructure is stable:

1. Add tests for remaining components to reach 70% coverage
2. Implement visual regression testing for UI consistency
3. Add performance tests for critical user paths
4. Create automated accessibility tests