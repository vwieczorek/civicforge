import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import QuestAttestationForm from '../QuestAttestationForm';
import { server } from '../../../mocks/server';
import { createMockQuest } from '../../../test/mocks/factory';
import { QuestStatus } from '../../../api/types';
import { config } from '../../../config';

// Mock the QuestAttestationWithSignature component since it has wallet dependencies
vi.mock('../QuestAttestationWithSignature', () => ({
  default: ({ onAttest }: { onAttest: (signature: string) => void }) => (
    <div data-testid="signature-attestation">
      <button onClick={() => onAttest('0xmocksignature')}>
        Sign and Attest
      </button>
    </div>
  ),
}));

describe('QuestAttestationForm', () => {
  const defaultQuestId = 'quest-123';
  const currentUserId = 'user-123';
  const creatorId = 'creator-456';
  const performerId = 'performer-789';
  const onSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading and Error States', () => {
    it('shows loading state while fetching quest data', async () => {
      // Delay the response to ensure we see the loading state
      server.use(
        http.get(`${config.API_BASE_URL}/api/v1/quests/:id`, async () => {
          await new Promise(resolve => setTimeout(resolve, 100));
          return HttpResponse.json(createMockQuest());
        })
      );

      render(
        <QuestAttestationForm 
          questId={defaultQuestId}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText('Loading...')).toBeInTheDocument();
      
      // Wait for the quest to load
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });
    });

    it('handles quest fetch errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      server.use(
        http.get(`${config.API_BASE_URL}/api/v1/quests/:id`, () => {
          return HttpResponse.json(
            { detail: 'Quest not found' },
            { status: 404 }
          );
        })
      );

      render(
        <QuestAttestationForm 
          questId={defaultQuestId}
          onSuccess={onSuccess}
        />
      );

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled();
      });

      consoleError.mockRestore();
    });

    it('uses provided quest prop without fetching', async () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={currentUserId}
          onSuccess={onSuccess}
        />
      );

      // Should not show loading state
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      
      // Should show attestation UI immediately
      expect(screen.getByText('Dual-Attestation Verification')).toBeInTheDocument();
    });
  });

  describe('UI Rendering', () => {
    it('renders attestation progress correctly', async () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
        attestations: [
          {
            user_id: creatorId,
            role: 'requestor',
            attested_at: new Date().toISOString(),
          }
        ],
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={performerId}
          onSuccess={onSuccess}
        />
      );

      // Check progress bar text
      expect(screen.getByText('1 of 2 attestations')).toBeInTheDocument();
      
      // Check attestation status indicators
      expect(screen.getByText('✓')).toBeInTheDocument(); // Requestor attested
      expect(screen.getByText('○')).toBeInTheDocument(); // Performer not attested
    });

    it('shows submission text when available', () => {
      const submissionText = 'I have completed the quest successfully!';
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        submissionText,
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText('Submission')).toBeInTheDocument();
      expect(screen.getByText(submissionText)).toBeInTheDocument();
    });

    it('shows completion message when quest is fully attested', () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.COMPLETE,
        rewardXp: 100,
        rewardReputation: 10,
        attestations: [
          {
            user_id: creatorId,
            role: 'requestor',
            attested_at: new Date().toISOString(),
          },
          {
            user_id: performerId,
            role: 'performer',
            attested_at: new Date().toISOString(),
          }
        ],
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText(/Quest completed! The performer has been awarded 100 XP and 10 reputation/)).toBeInTheDocument();
    });

    it('does not render when quest status is not SUBMITTED or COMPLETE', () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.OPEN,
      });

      const { container } = render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('Role-Based Access Control', () => {
    it.each([
      { userRole: 'requestor', userId: creatorId, canAttest: true },
      { userRole: 'performer', userId: performerId, canAttest: true },
      { userRole: 'other', userId: 'random-user', canAttest: false },
    ])('$userRole can attest: $canAttest', ({ userId, canAttest }) => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
        attestations: [],
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={userId}
          onSuccess={onSuccess}
        />
      );

      if (canAttest) {
        expect(screen.getByRole('button', { name: /Attest Completion/i })).toBeInTheDocument();
      } else {
        expect(screen.queryByRole('button', { name: /Attest Completion/i })).not.toBeInTheDocument();
        expect(screen.getByText('You are not authorized to attest this quest.')).toBeInTheDocument();
      }
    });

    it('shows waiting message when user has already attested', () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
        attestations: [
          {
            user_id: creatorId,
            role: 'requestor',
            attested_at: new Date().toISOString(),
          }
        ],
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText('You have attested. Waiting for the other party to attest.')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Attest Completion/i })).not.toBeInTheDocument();
    });

    it('identifies current user role correctly', () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      const { rerender } = render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText('Requestor (You)')).toBeInTheDocument();

      rerender(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={performerId}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText('Performer (You)')).toBeInTheDocument();
    });
  });

  describe('Simple Attestation Flow', () => {
    it('submits attestation successfully', async () => {
      const user = userEvent.setup();
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      server.use(
        http.post(`${config.API_BASE_URL}/api/v1/quests/:id/attest`, async ({ params }) => {
          expect(params.id).toBe(defaultQuestId);
          return HttpResponse.json(createMockQuest({
            ...mockQuest,
            attestations: [{
              user_id: creatorId,
              role: 'requestor',
              attested_at: new Date().toISOString(),
            }],
          }));
        })
      );

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
      await user.click(attestButton);

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it('shows error message when attestation fails', async () => {
      const user = userEvent.setup();
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      server.use(
        http.post(`${config.API_BASE_URL}/api/v1/quests/:id/attest`, () => {
          return HttpResponse.json(
            { detail: 'Attestation failed' },
            { status: 400 }
          );
        })
      );

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
      await user.click(attestButton);

      await waitFor(() => {
        // The actual error message shown is "Attestation failed" based on the test output
        expect(screen.getByText('Attestation failed')).toBeInTheDocument();
      });

      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('disables button while submitting', async () => {
      const user = userEvent.setup();
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      let resolveAttestation: (value: any) => void;
      const attestationPromise = new Promise((resolve) => {
        resolveAttestation = resolve;
      });

      server.use(
        http.post(`${config.API_BASE_URL}/api/v1/quests/:id/attest`, async () => {
          await attestationPromise;
          return HttpResponse.json(mockQuest);
        })
      );

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
      await user.click(attestButton);

      // Button should be disabled and show loading text
      expect(attestButton).toBeDisabled();
      expect(attestButton).toHaveTextContent('Attesting...');

      // Resolve the promise
      resolveAttestation!(true);

      await waitFor(() => {
        expect(attestButton).not.toBeDisabled();
      });
    });
  });

  describe('Cryptographic Signature Flow', () => {
    it('toggles between simple and cryptographic attestation', async () => {
      const user = userEvent.setup();
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      // Initially shows simple attestation
      expect(screen.getByRole('button', { name: /Attest Completion/i })).toBeInTheDocument();
      expect(screen.queryByTestId('signature-attestation')).not.toBeInTheDocument();

      // Toggle to cryptographic attestation
      const toggleButton = screen.getByRole('button', { name: /Use Cryptographic Attestation/i });
      await user.click(toggleButton);

      // Should now show signature component
      expect(screen.queryByRole('button', { name: /Attest Completion/i })).not.toBeInTheDocument();
      expect(screen.getByTestId('signature-attestation')).toBeInTheDocument();

      // Toggle back
      await user.click(screen.getByRole('button', { name: /Use Simple Attestation/i }));
      expect(screen.getByRole('button', { name: /Attest Completion/i })).toBeInTheDocument();
    });

    it('submits attestation with signature', async () => {
      const user = userEvent.setup();
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      server.use(
        http.post(`${config.API_BASE_URL}/api/v1/quests/:id/attest`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.signature).toBe('0xmocksignature');
          return HttpResponse.json(createMockQuest({
            ...mockQuest,
            attestations: [{
              user_id: creatorId,
              role: 'requestor',
              attested_at: new Date().toISOString(),
              signature: body.signature,
            }],
          }));
        })
      );

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      // Toggle to cryptographic attestation
      await user.click(screen.getByRole('button', { name: /Use Cryptographic Attestation/i }));

      // Click the mocked sign and attest button
      await user.click(screen.getByRole('button', { name: /Sign and Attest/i }));

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles missing attestations array gracefully', () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
        attestations: undefined as any, // Force undefined
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      // Should default to empty array and show 0 attestations
      expect(screen.getByText('0 of 2 attestations')).toBeInTheDocument();
    });

    it('handles null currentUserId', () => {
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      render(
        <QuestAttestationForm 
          quest={mockQuest}
          currentUserId={null as any}
          onSuccess={onSuccess}
        />
      );

      // Should show unauthorized message
      expect(screen.getByText('You are not authorized to attest this quest.')).toBeInTheDocument();
    });

    it('updates UI after successful attestation without page refresh', async () => {
      const user = userEvent.setup();
      const mockQuest = createMockQuest({
        questId: defaultQuestId,
        status: QuestStatus.SUBMITTED,
        creatorId,
        performerId,
      });

      server.use(
        http.get(`${config.API_BASE_URL}/api/v1/quests/:id`, () => {
          return HttpResponse.json(mockQuest);
        }),
        http.post(`${config.API_BASE_URL}/api/v1/quests/:id/attest`, () => {
          // Return quest with attestation added
          return HttpResponse.json({
            ...mockQuest,
            attestations: [{
              user_id: creatorId,
              role: 'requestor',
              attested_at: new Date().toISOString(),
            }],
          });
        })
      );

      render(
        <QuestAttestationForm 
          questId={defaultQuestId}
          currentUserId={creatorId}
          onSuccess={onSuccess}
        />
      );

      // Wait for quest to load
      await waitFor(() => {
        expect(screen.getByText('Dual-Attestation Verification')).toBeInTheDocument();
      });

      // Attest
      const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
      await user.click(attestButton);

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });
  });
});