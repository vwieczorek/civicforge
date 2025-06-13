/**
 * App component test
 * Tests basic rendering and routing setup
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

// Mock AWS Amplify
vi.mock('aws-amplify', () => ({
  Amplify: {
    configure: vi.fn(),
  },
}));

// Mock getCurrentUser to simulate authenticated state
vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: vi.fn().mockResolvedValue({ userId: 'test-user' }),
}));

// Mock the Authenticator component
vi.mock('@aws-amplify/ui-react', () => ({
  Authenticator: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuthenticator: () => ({
    user: { userId: 'test-user' },
    signOut: vi.fn(),
  }),
}));

describe('App', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // App should render the main structure
    expect(container.querySelector('.app')).toBeInTheDocument();
  });

  it('renders navigation header', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // Check for navigation elements
    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);
  });

  it('shows authentication state in header', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // Should eventually show sign in link (since we mocked as authenticated)
    await waitFor(() => {
      expect(screen.getByText(/sign out/i)).toBeInTheDocument();
    });
  });

  it('configures Amplify on module load', () => {
    const { Amplify } = require('aws-amplify');
    
    // Amplify.configure is called when the module loads, not on mount
    expect(Amplify.configure).toHaveBeenCalled();
  });
});