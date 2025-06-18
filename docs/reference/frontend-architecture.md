# Frontend Architecture Guide

*Last Updated: January 2025*

## Overview

The CivicForge frontend is a modern React application built with TypeScript, designed for scalability, maintainability, and exceptional user experience. This guide provides a comprehensive overview of the frontend architecture, patterns, and best practices.

## Technology Stack

### Core Technologies
- **React 18**: UI library with concurrent features
- **TypeScript 4.9+**: Type-safe development
- **Vite**: Fast build tool and dev server
- **React Router v6**: Client-side routing
- **AWS Amplify Auth**: Authentication integration

### Development Tools
- **Vitest**: Unit testing framework
- **React Testing Library**: Component testing
- **Playwright**: E2E testing
- **MSW**: API mocking for tests
- **ESLint & Prettier**: Code quality

## Architecture Principles

### 1. Component-Based Architecture
We follow a component-based architecture with clear separation of concerns:

```
src/
├── components/          # Reusable UI components
│   ├── common/         # Generic components (Button, Modal, etc.)
│   ├── auth/           # Authentication-related components
│   └── quests/         # Quest-specific components
├── views/              # Page-level components
├── hooks/              # Custom React hooks
├── api/                # API client and types
├── utils/              # Utility functions
└── types/              # TypeScript type definitions
```

### 2. State Management
We use React's built-in state management solutions:

- **Local State**: `useState` for component-specific state
- **Context API**: For cross-cutting concerns (auth, theme)
- **Custom Hooks**: For complex state logic
- **Server State**: Direct API calls with loading states

Example of our auth context pattern:
```typescript
// contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### 3. Data Fetching Pattern
We use a consistent pattern for API interactions:

```typescript
// Example: Quest fetching hook
export function useQuest(questId: string) {
  const [quest, setQuest] = useState<Quest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchQuest() {
      try {
        setIsLoading(true);
        const data = await apiClient.getQuest(questId);
        setQuest(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchQuest();
  }, [questId]);

  return { quest, isLoading, error };
}
```

## Component Structure

### Component Organization
Each component follows this structure:
```
components/
└── quests/
    └── QuestCard/
        ├── QuestCard.tsx       # Component implementation
        ├── QuestCard.test.tsx  # Unit tests
        ├── QuestCard.css       # Styles
        └── index.ts            # Public API
```

### Component Patterns

#### 1. Presentational Components
Pure components that receive props and render UI:
```typescript
interface QuestCardProps {
  quest: Quest;
  onClaim?: (questId: string) => void;
  isClaimable?: boolean;
}

export function QuestCard({ quest, onClaim, isClaimable = true }: QuestCardProps) {
  return (
    <div className="quest-card">
      <h3>{quest.title}</h3>
      <p>{quest.description}</p>
      {isClaimable && (
        <button onClick={() => onClaim?.(quest.questId)}>
          Claim Quest
        </button>
      )}
    </div>
  );
}
```

#### 2. Container Components
Components that manage state and business logic:
```typescript
export function QuestListContainer() {
  const { quests, isLoading, error } = useQuests();
  const { claimQuest } = useQuestActions();

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorBoundary error={error} />;

  return (
    <QuestList 
      quests={quests}
      onClaimQuest={claimQuest}
    />
  );
}
```

## Routing Architecture

We use React Router v6 with protected routes:

```typescript
// App.tsx routing structure
<Routes>
  {/* Public routes */}
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  
  {/* Protected routes */}
  <Route element={<ProtectedRoute />}>
    <Route path="/" element={<QuestList />} />
    <Route path="/quests/:questId" element={<QuestDetail />} />
    <Route path="/create-quest" element={<CreateQuest />} />
    <Route path="/profile/:userId" element={<UserProfile />} />
  </Route>
  
  <Route path="*" element={<NotFound />} />
</Routes>
```

## API Integration

### API Client Architecture
Our API client provides a type-safe interface to the backend:

```typescript
// api/client.ts
class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.authToken && { Authorization: `Bearer ${this.authToken}` }),
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }

  // Typed methods for each endpoint
  async getQuests(filters?: QuestFilters): Promise<Quest[]> {
    const params = new URLSearchParams(filters as any);
    return this.request<Quest[]>(`/quests?${params}`);
  }
}
```

### Error Handling
Centralized error handling with user-friendly messages:

```typescript
// hooks/useErrorHandler.ts
export function useErrorHandler() {
  const { showNotification } = useNotification();

  const handleError = useCallback((error: unknown) => {
    console.error('Error occurred:', error);

    if (error instanceof ApiError) {
      switch (error.status) {
        case 401:
          showNotification('Please log in to continue', 'error');
          break;
        case 403:
          showNotification('You don\'t have permission to do that', 'error');
          break;
        case 404:
          showNotification('Resource not found', 'error');
          break;
        default:
          showNotification('Something went wrong. Please try again.', 'error');
      }
    } else {
      showNotification('An unexpected error occurred', 'error');
    }
  }, [showNotification]);

  return { handleError };
}
```

## Testing Strategy

### Unit Testing
Component testing with Vitest and React Testing Library:

```typescript
// QuestCard.test.tsx
describe('QuestCard', () => {
  it('renders quest information', () => {
    const quest = createMockQuest();
    render(<QuestCard quest={quest} />);
    
    expect(screen.getByText(quest.title)).toBeInTheDocument();
    expect(screen.getByText(quest.description)).toBeInTheDocument();
  });

  it('calls onClaim when claim button clicked', async () => {
    const quest = createMockQuest();
    const onClaim = vi.fn();
    
    render(<QuestCard quest={quest} onClaim={onClaim} />);
    
    await userEvent.click(screen.getByText('Claim Quest'));
    expect(onClaim).toHaveBeenCalledWith(quest.questId);
  });
});
```

### Integration Testing
Testing component interactions with mocked API:

```typescript
// QuestList.integration.test.tsx
describe('QuestList Integration', () => {
  beforeEach(() => {
    server.use(
      rest.get('/api/v1/quests', (req, res, ctx) => {
        return res(ctx.json(mockQuests));
      })
    );
  });

  it('loads and displays quests', async () => {
    render(<QuestList />);
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText(mockQuests[0].title)).toBeInTheDocument();
    });
  });
});
```

### E2E Testing
Critical user flows with Playwright:

```typescript
// e2e/quest-lifecycle.spec.ts
test('complete quest lifecycle', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  // Create quest
  await page.click('text=Create Quest');
  await page.fill('[name="title"]', 'Test Quest');
  await page.fill('[name="description"]', 'Test Description');
  await page.click('text=Create');

  // Verify quest appears in list
  await expect(page.locator('text=Test Quest')).toBeVisible();
});
```

## Performance Optimization

### Code Splitting
Route-based code splitting for optimal bundle sizes:

```typescript
// Lazy load routes
const QuestDetail = lazy(() => import('./views/QuestDetail'));
const UserProfile = lazy(() => import('./views/UserProfile'));

// Wrap with Suspense
<Suspense fallback={<LoadingSkeleton />}>
  <Routes>
    <Route path="/quests/:id" element={<QuestDetail />} />
    <Route path="/profile/:id" element={<UserProfile />} />
  </Routes>
</Suspense>
```

### Memoization
Optimize expensive computations and renders:

```typescript
// Memoized component
export const QuestCard = memo(({ quest, onClaim }: QuestCardProps) => {
  return <div>...</div>;
});

// Memoized values
const filteredQuests = useMemo(
  () => quests.filter(q => q.status === filter),
  [quests, filter]
);

// Memoized callbacks
const handleClaim = useCallback(
  (questId: string) => {
    claimQuest(questId);
  },
  [claimQuest]
);
```

### Image Optimization
Lazy loading and responsive images:

```typescript
export function QuestImage({ src, alt }: ImageProps) {
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      className="quest-image"
    />
  );
}
```

## Security Best Practices

### XSS Prevention
- All user input is sanitized using DOMPurify
- React automatically escapes values in JSX
- Dangerous properties like `dangerouslySetInnerHTML` are avoided

### Authentication Security
- JWT tokens stored in memory, not localStorage
- Refresh tokens handled securely
- Automatic token refresh before expiration
- Protected routes check authentication state

### API Security
- HTTPS enforced in production
- CORS properly configured
- Input validation on all forms
- Rate limiting awareness in UI

## Styling Architecture

### CSS Organization
We use CSS modules for component styles:

```css
/* QuestCard.module.css */
.questCard {
  padding: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.questCard:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
```

### Design System Variables
Global design tokens in CSS variables:

```css
/* globals.css */
:root {
  /* Colors */
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --danger-color: #dc3545;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  
  /* Typography */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-size-base: 1rem;
  --line-height-base: 1.5;
}
```

## Build and Deployment

### Build Configuration
Vite configuration for optimal production builds:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          auth: ['@aws-amplify/auth'],
        },
      },
    },
  },
  define: {
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL),
  },
});
```

### Environment Configuration
Environment-specific configuration:

```typescript
// config.ts
export const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:3001',
  cognitoRegion: import.meta.env.VITE_AWS_REGION || 'us-east-1',
  userPoolId: import.meta.env.VITE_USER_POOL_ID,
  userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
};
```

## Monitoring and Analytics

### Error Tracking
Integration with error tracking service:

```typescript
// utils/errorTracking.ts
export function trackError(error: Error, context?: Record<string, any>) {
  console.error('Error:', error);
  
  // In production, send to error tracking service
  if (import.meta.env.PROD) {
    // Sentry, Rollbar, etc.
  }
}
```

### Performance Monitoring
Web Vitals tracking:

```typescript
// utils/webVitals.ts
export function reportWebVitals(metric: Metric) {
  console.log(metric);
  
  // Send to analytics
  if (import.meta.env.PROD) {
    // Google Analytics, etc.
  }
}
```

## Future Enhancements

### Planned Improvements
1. **State Management**: Consider Zustand or Jotai for complex state
2. **Real-time Updates**: WebSocket integration for live updates
3. **Offline Support**: Service Worker for offline functionality
4. **Mobile App**: React Native version sharing core logic
5. **Internationalization**: i18n support for multiple languages

### Performance Goals
- First Contentful Paint < 1.5s
- Time to Interactive < 3.5s
- Lighthouse score > 90
- Bundle size < 200KB (gzipped)

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check Cognito configuration
   - Verify token refresh logic
   - Check CORS settings

2. **Build Failures**
   - Clear node_modules and reinstall
   - Check TypeScript errors
   - Verify environment variables

3. **Test Failures**
   - Check MSW handlers match API
   - Verify test environment setup
   - Look for timing issues in async tests

### Debug Tools
- React DevTools for component inspection
- Network tab for API debugging
- Console for error messages
- Lighthouse for performance audits

## Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [React Router Tutorial](https://reactrouter.com/en/main/start/tutorial)