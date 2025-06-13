import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import QuestDetail from '../QuestDetail';
import { server } from '../../mocks/server';
import { http, HttpResponse } from 'msw';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate
  };
});

// Import auth functions from the already mocked module
import { getCurrentUser } from 'aws-amplify/auth';

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn()
  }
}));

describe('QuestDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCurrentUser).mockResolvedValue({
      userId: 'user-123',
      username: 'testuser'
    });
  });

  it('renders quest details', async () => {
    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Quest')).toBeInTheDocument();
      expect(screen.getByText('Test quest description')).toBeInTheDocument();
      expect(screen.getByText(/100/)).toBeInTheDocument(); // XP
      expect(screen.getByText(/10/)).toBeInTheDocument(); // Reputation
    });
  });

  it('shows claim button for open quests', async () => {
    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /claim quest/i })).toBeInTheDocument();
    });
  });

  it('handles quest claiming', async () => {
    const user = userEvent.setup();
    
    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /claim quest/i })).toBeInTheDocument();
    });

    const claimButton = screen.getByRole('button', { name: /claim quest/i });
    await user.click(claimButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit completed work/i })).toBeInTheDocument();
    });
  });

  it('shows submit button for quest holder', async () => {
    // Override the handler to return quest with current holder
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:id', ({ params }) => {
        return HttpResponse.json({
          questId: params.id,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'CLAIMED',
          performerId: 'user-123', // Current user is the holder
          attestations: [],
          createdAt: new Date().toISOString(),
          claimedAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit completed work/i })).toBeInTheDocument();
    });
  });

  it('handles quest submission', async () => {
    const user = userEvent.setup();
    
    // Set up quest with current user as holder
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:id', ({ params }) => {
        return HttpResponse.json({
          id: params.id,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          reward: 50,
          status: 'IN_PROGRESS',
          currentHolder: 'user-123',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit completed work/i })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /submit completed work/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/pending review/i)).toBeInTheDocument();
    });
  });

  it('shows attest button for quest creator when pending review', async () => {
    // Set up quest created by current user in pending review
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:id', ({ params }) => {
        return HttpResponse.json({
          id: params.id,
          creatorId: 'user-123', // Current user is creator
          title: 'Test Quest',
          description: 'Test quest description',
          reward: 50,
          status: 'PENDING_REVIEW',
          currentHolder: 'user-456',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /attest completion/i })).toBeInTheDocument();
    });
  });

  it('handles quest attestation without signature', async () => {
    const user = userEvent.setup();
    
    // Set up quest for attestation
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:id', ({ params }) => {
        return HttpResponse.json({
          id: params.id,
          creatorId: 'user-123',
          title: 'Test Quest',
          description: 'Test quest description',
          reward: 50,
          status: 'PENDING_REVIEW',
          currentHolder: 'user-456',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /attest completion/i })).toBeInTheDocument();
    });

    const attestButton = screen.getByRole('button', { name: /attest completion/i });
    await user.click(attestButton);

    // Should show attestation form
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit attestation/i })).toBeInTheDocument();
    });

    // Submit without signature
    const submitButton = screen.getByRole('button', { name: /submit attestation/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/attested/i)).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    // Set up error response
    server.use(
      http.get('http://localhost:3001/quests/:id', () => {
        return HttpResponse.json(
          { error: 'Quest not found' },
          { status: 404 }
        );
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error loading quest/i)).toBeInTheDocument();
    });
  });

  it('shows delete button for quest creator', async () => {
    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /delete quest/i })).toBeInTheDocument();
    });
  });

  it('handles quest deletion', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:id" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /delete quest/i })).toBeInTheDocument();
    });

    const deleteButton = screen.getByRole('button', { name: /delete quest/i });
    await user.click(deleteButton);

    // Confirm deletion (if there's a confirmation dialog)
    // await user.click(screen.getByRole('button', { name: /confirm/i }));

    await waitFor(() => {
      expect(screen.queryByText('Test Quest')).not.toBeInTheDocument();
    });
  });
});