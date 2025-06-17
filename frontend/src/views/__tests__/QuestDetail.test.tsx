import { describe, it, expect, vi, beforeEach } from 'vitest';
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
    // Add explicit MSW handler for this test
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'OPEN',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Quest')).toBeInTheDocument();
      expect(screen.getByText('Test quest description')).toBeInTheDocument();
      expect(screen.getByText(/100/)).toBeInTheDocument(); // XP
      expect(screen.getByText(/\+10/)).toBeInTheDocument(); // Reputation
    });
  });

  it('shows claim button for open quests', async () => {
    // Add explicit MSW handler for OPEN quest
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'OPEN',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /claim quest/i })).toBeInTheDocument();
    });
  });

  it('handles quest claiming', async () => {
    const user = userEvent.setup();
    
    // Mock the initial GET for an OPEN quest
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'OPEN',
          attestations: [],
          createdAt: new Date().toISOString(),
        });
      }, { once: true }) // This handler will only be used once
    );

    // Mock the subsequent GET to return a CLAIMED quest
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          performerId: null, // Not claimed yet
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'OPEN', // Available to claim
          attestations: [],
          createdAt: new Date().toISOString(),
        });
      }, { once: true }),
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          performerId: 'user-123', // Current user has claimed it
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'CLAIMED', // Now claimed
          attestations: [],
          createdAt: new Date().toISOString(),
        });
      })
    );
    
    // Mock the POST /claim endpoint
    server.use(
      http.post('http://localhost:3001/api/v1/quests/:questId/claim', () => {
        return HttpResponse.json({}, { status: 200 });
      })
    );
    
    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
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
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit completed work/i })).toBeInTheDocument();
    });
  });

  it('handles quest submission', async () => {
    const user = userEvent.setup();
    
    // Set up quest with current user as holder (CLAIMED state)
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'CLAIMED',
          performerId: 'user-123',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      }, { once: true }),
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-456',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 100,
          rewardReputation: 10,
          status: 'SUBMITTED',
          performerId: 'user-123',
          submissionText: 'I have completed the quest!',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      }),
      http.post('http://localhost:3001/api/v1/quests/:questId/submit', () => {
        return HttpResponse.json({}, { status: 200 });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit completed work/i })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /submit completed work/i });
    await user.click(submitButton);

    // Wait for the modal to appear
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Submit Completed Work' })).toBeInTheDocument();
    });

    // Fill in the submission text
    const textArea = screen.getByPlaceholderText(/Explain what you did to complete this quest/i);
    await user.type(textArea, 'Test submission');

    // Submit the form
    const modalSubmitButton = screen.getByRole('button', { name: /submit work/i });
    await user.click(modalSubmitButton);

    await waitFor(() => {
      expect(screen.getByText('SUBMITTED')).toBeInTheDocument();
    });
  });

  it('shows attest button for quest creator when pending review', async () => {
    // Set up quest created by current user in pending review
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:id', ({ params }) => {
        return HttpResponse.json({
          questId: params.id,
          creatorId: 'user-123', // Current user is creator
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 50,
          rewardReputation: 5,
          status: 'SUBMITTED',
          performerId: 'user-456',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Attestation Required')).toBeInTheDocument();
    });
  });

  it('handles quest attestation without signature', async () => {
    const user = userEvent.setup();
    
    // Mock the current user as the quest creator
    vi.mocked(getCurrentUser).mockResolvedValue({
      userId: 'user-123',
      username: 'testuser'
    });
    
    // Set up quest for attestation
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-123',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 50,
          rewardReputation: 5,
          status: 'SUBMITTED',
          performerId: 'user-456',
          submissionText: 'Quest completed!',
          attestations: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      }, { once: true }),
      http.get('http://localhost:3001/api/v1/quests/:questId', ({ params }) => {
        return HttpResponse.json({
          questId: params.questId,
          creatorId: 'user-123',
          title: 'Test Quest',
          description: 'Test quest description',
          rewardXp: 50,
          rewardReputation: 5,
          status: 'COMPLETE',
          performerId: 'user-456',
          submissionText: 'Quest completed!',
          attestations: [
            { user_id: 'user-123', role: 'requestor', attestedAt: new Date().toISOString() },
            { user_id: 'user-456', role: 'performer', attestedAt: new Date().toISOString() }
          ],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      }),
      http.post('http://localhost:3001/api/v1/quests/:questId/attest', () => {
        return HttpResponse.json({}, { status: 200 });
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Attestation Required')).toBeInTheDocument();
    });

    // Wait for the QuestAttestationForm to fully load
    await waitFor(() => {
      expect(screen.getByText(/Both the requestor and performer must attest/i)).toBeInTheDocument();
    });

    const attestButton = await screen.findByRole('button', { name: 'Attest Completion' });
    await user.click(attestButton);

    // After clicking attest, verify the UI updated to show the user's attestation
    await waitFor(() => {
      // Check that the user's attestation is now displayed
      expect(screen.getByText('Your Attestation')).toBeInTheDocument();
      // And the quest status should show as COMPLETE
      expect(screen.getByText('COMPLETE')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    // Set up error response
    server.use(
      http.get('http://localhost:3001/api/v1/quests/:questId', () => {
        return HttpResponse.json(
          { error: 'Quest not found' },
          { status: 404 }
        );
      })
    );

    render(
      <MemoryRouter initialEntries={['/quests/quest-123']}>
        <Routes>
          <Route path="/quests/:questId" element={<QuestDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load quest details/i)).toBeInTheDocument();
    });
  });

});