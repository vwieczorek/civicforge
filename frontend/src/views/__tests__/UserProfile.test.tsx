import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import UserProfile from '../UserProfile';
import { server } from '../../mocks/server';
import { http, HttpResponse } from 'msw';
import { getCurrentUser } from 'aws-amplify/auth';

describe('UserProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock a logged-in user
    vi.mocked(getCurrentUser).mockResolvedValue({
      userId: 'user-123',
      username: 'testuser',
    });
  });

  it('renders user profile data', async () => {
    render(
      <MemoryRouter initialEntries={['/users/user-123']}>
        <Routes>
          <Route path="/users/:userId" element={<UserProfile />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
      
      const reputationLabel = screen.getByText('Reputation');
      expect(reputationLabel.previousElementSibling).toHaveTextContent('85');

      const experienceLabel = screen.getByText('Experience');
      expect(experienceLabel.previousElementSibling).toHaveTextContent('1500');

      const createdQuestsLabel = screen.getByText('Quests Created');
      expect(createdQuestsLabel.previousElementSibling).toHaveTextContent('0');
    });
  });

  it('shows loading state', () => {
    // Override handler to delay response
    server.use(
      http.get('http://localhost:3001/api/v1/users/:id', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        return HttpResponse.json({});
      })
    );

    render(
      <MemoryRouter initialEntries={['/users/user-123']}>
        <Routes>
          <Route path="/users/:userId" element={<UserProfile />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/loading profile/i)).toBeInTheDocument();
  });

  it('handles user not found', async () => {
    server.use(
      http.get('http://localhost:3001/api/v1/users/:id', () => {
        return HttpResponse.json(
          { error: 'User not found' },
          { status: 404 }
        );
      })
    );

    render(
      <MemoryRouter initialEntries={['/users/unknown-user']}>
        <Routes>
          <Route path="/users/:userId" element={<UserProfile />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/user not found/i)).toBeInTheDocument();
    });
  });

  it('displays reputation score', async () => {
    render(
      <MemoryRouter initialEntries={['/users/user-123']}>
        <Routes>
          <Route path="/users/:userId" element={<UserProfile />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const reputationLabel = screen.getByText('Reputation');
      expect(reputationLabel.previousElementSibling).toHaveTextContent('85');
    });
  });

  it('displays attestation statistics', async () => {
    render(
      <MemoryRouter initialEntries={['/users/user-123']}>
        <Routes>
          <Route path="/users/:userId" element={<UserProfile />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
      // These stats are part of the user profile component
      expect(screen.getByText('Reputation')).toBeInTheDocument();
    });
  });
});