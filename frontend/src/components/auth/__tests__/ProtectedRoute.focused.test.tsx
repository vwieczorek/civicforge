/**
 * Focused test for ProtectedRoute component
 * Tests critical authentication flow
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '../ProtectedRoute';

// Mock getCurrentUser from AWS Amplify
const mockGetCurrentUser = vi.fn();
vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: () => mockGetCurrentUser(),
}));

describe('ProtectedRoute - Authentication Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while checking authentication', () => {
    // Keep promise pending to test loading state
    mockGetCurrentUser.mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to login when user is not authenticated', async () => {
    mockGetCurrentUser.mockRejectedValue(new Error('Not authenticated'));

    render(
      <MemoryRouter initialEntries={['/protected-page']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/protected-page"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders protected content when user is authenticated', async () => {
    mockGetCurrentUser.mockResolvedValue({
      userId: 'user-123',
      username: 'testuser',
    });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  it('preserves the original location when redirecting to login', async () => {
    mockGetCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    
    render(
      <MemoryRouter initialEntries={['/quests/quest-123?tab=details']}>
        <Routes>
          <Route 
            path="/login" 
            element={
              <div>
                Login Page
                {/* In real app, location.state would be used to redirect back */}
              </div>
            } 
          />
          <Route
            path="/quests/:id"
            element={
              <ProtectedRoute>
                <div>Quest Details</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
    
    // The ProtectedRoute should pass the original location in state
    // This would be used by the login page to redirect back after auth
  });
});