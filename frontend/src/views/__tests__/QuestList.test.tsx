import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import QuestList from '../QuestList';
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

describe('QuestList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders quest list', async () => {
    render(
      <MemoryRouter>
        <QuestList />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Quest')).toBeInTheDocument();
      expect(screen.getByText('Test quest description')).toBeInTheDocument();
      expect(screen.getByText(/100/)).toBeInTheDocument(); // XP value
      expect(screen.getByText(/10/)).toBeInTheDocument(); // Reputation value
    });
  });

  it('shows loading state', () => {
    // Override handler to delay response
    server.use(
      http.get('http://localhost:3001/api/v1/quests', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        return HttpResponse.json([]);
      })
    );

    render(
      <MemoryRouter>
        <QuestList />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading quests/i)).toBeInTheDocument();
  });

  it('shows empty state when no quests', async () => {
    server.use(
      http.get('http://localhost:3001/api/v1/quests', () => {
        return HttpResponse.json([]);
      })
    );

    render(
      <MemoryRouter>
        <QuestList />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no quests available/i)).toBeInTheDocument();
    });
  });

  it('handles API errors', async () => {
    server.use(
      http.get('http://localhost:3001/api/v1/quests', () => {
        return HttpResponse.json(
          { error: 'Server error' },
          { status: 500 }
        );
      })
    );

    render(
      <MemoryRouter>
        <QuestList />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error loading quests/i)).toBeInTheDocument();
    });
  });

  it('displays quest status badges', async () => {
    server.use(
      http.get('http://localhost:3001/api/v1/quests', () => {
        return HttpResponse.json([
          {
            questId: 'quest-1',
            creatorId: 'user-123',
            title: 'Open Quest',
            description: 'An open quest',
            rewardXp: 50,
            rewardReputation: 5,
            status: 'OPEN',
            performerId: null,
            attestations: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          },
          {
            questId: 'quest-2',
            creatorId: 'user-456',
            title: 'In Progress Quest',
            description: 'A quest in progress',
            rewardXp: 75,
            rewardReputation: 7,
            status: 'CLAIMED',
            performerId: 'user-789',
            attestations: [],
            createdAt: new Date().toISOString(),
            claimedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          },
          {
            questId: 'quest-3',
            creatorId: 'user-111',
            title: 'Completed Quest',
            description: 'A completed quest',
            rewardXp: 100,
            rewardReputation: 10,
            status: 'COMPLETE',
            performerId: 'user-222',
            attestations: [{ user_id: 'user-111', role: 'requestor', attested_at: new Date().toISOString() }],
            createdAt: new Date().toISOString(),
            completedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          }
        ]);
      })
    );

    render(
      <MemoryRouter>
        <QuestList />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('OPEN')).toBeInTheDocument();
      expect(screen.getByText('CLAIMED')).toBeInTheDocument();
      expect(screen.getByText('COMPLETE')).toBeInTheDocument();
    });
  });

  it('navigates to quest detail on click', async () => {
    render(
      <MemoryRouter>
        <QuestList />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Quest')).toBeInTheDocument();
    });

    const questTitle = screen.getByText('Test Quest');
    questTitle.click();

    expect(mockNavigate).toHaveBeenCalledWith('/quests/quest-123');
  });
});