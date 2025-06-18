/**
 * Focused test for Quest Attestation flow
 * Tests the critical dual-attestation mechanism
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QuestAttestationForm from '../QuestAttestationForm';
import { createTestScenario } from '../../../test/mocks/factory';
import { api } from '../../../api/client';
import { QuestStatus } from '../../../api/types';

describe('Quest Attestation - Critical Flow', () => {
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the API mocks
    vi.spyOn(api, 'getQuest').mockClear();
    vi.spyOn(api, 'attestQuest').mockClear();
  });

  it('renders attestation form with quest information', async () => {
    const { quest, currentUser } = createTestScenario('attestation');
    
    // Mock the API call if component needs to fetch
    vi.spyOn(api, 'getQuest').mockResolvedValue(quest);
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // The component should show the attestation form
    expect(screen.getByText('Dual-Attestation Verification')).toBeInTheDocument();
    expect(screen.getByText(/Both the requestor and performer must attest/i)).toBeInTheDocument();
    
    // Should show attestation progress
    expect(screen.getByText('Attestation Progress')).toBeInTheDocument();
    expect(screen.getByText('0 of 2 attestations')).toBeInTheDocument();
    
    // Should have the attest button for the current user (who is the creator/requestor)
    expect(screen.getByRole('button', { name: /Attest Completion/i })).toBeInTheDocument();
  });

  it('allows attestation without wallet signature', async () => {
    const { quest, currentUser } = createTestScenario('attestation');
    const user = userEvent.setup();
    
    // Mock successful attestation
    vi.spyOn(api, 'attestQuest').mockResolvedValue(undefined);
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // Click the attest button
    const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
    await user.click(attestButton);

    await waitFor(() => {
      expect(api.attestQuest).toHaveBeenCalledWith(quest.questId);
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('handles attestation errors gracefully', async () => {
    const { quest, currentUser } = createTestScenario('attestation');
    const user = userEvent.setup();
    
    // Mock API error
    vi.spyOn(api, 'attestQuest').mockRejectedValue(
      new Error('Failed to attest')
    );

    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
    await user.click(attestButton);

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText('Failed to attest')).toBeInTheDocument();
    });

    // onSuccess should not have been called
    expect(mockOnSuccess).not.toHaveBeenCalled();
  });

  it('shows loading state during attestation', async () => {
    const { quest, currentUser } = createTestScenario('attestation');
    const user = userEvent.setup();
    
    // Mock API with controlled promise
    let resolveAttest: () => void;
    const attestPromise = new Promise<void>((resolve) => {
      resolveAttest = resolve;
    });
    vi.spyOn(api, 'attestQuest').mockReturnValue(attestPromise);

    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    const attestButton = screen.getByRole('button', { name: /Attest Completion/i });
    await user.click(attestButton);

    // Button should show loading state
    expect(attestButton).toBeDisabled();
    expect(attestButton).toHaveTextContent('Attesting...');
    
    // Resolve the promise
    resolveAttest!();
    
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('shows correct state when user has already attested', () => {
    const { quest, currentUser } = createTestScenario('attestation');
    
    // Add attestation from current user
    quest.attestations = [{
      user_id: currentUser.userId,
      role: 'requestor',
      attested_at: new Date().toISOString(),
    }];
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // Should show 1 of 2 attestations
    expect(screen.getByText('1 of 2 attestations')).toBeInTheDocument();
    
    // Should show user has already attested
    expect(screen.getByText('You have attested. Waiting for the other party to attest.')).toBeInTheDocument();
    
    // Should not show attest button
    expect(screen.queryByRole('button', { name: /Attest Completion/i })).not.toBeInTheDocument();
  });

  it('shows completion message when quest is fully attested', () => {
    const { quest, currentUser, otherUser } = createTestScenario('attestation');
    
    // Add both attestations and mark as complete
    quest.attestations = [
      {
        user_id: currentUser.userId,
        role: 'requestor',
        attested_at: new Date().toISOString(),
      },
      {
        user_id: otherUser.userId,
        role: 'performer',
        attested_at: new Date().toISOString(),
      }
    ];
    quest.status = QuestStatus.COMPLETE;
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // Should show completion message with rewards
    const successMessage = screen.getByText(/Quest completed!/);
    expect(successMessage).toBeInTheDocument();
    expect(successMessage.textContent).toContain(`${quest.rewardXp} XP`);
    expect(successMessage.textContent).toContain(`${quest.rewardReputation} reputation`);
    
    // Should not show attest button
    expect(screen.queryByRole('button', { name: /Attest Completion/i })).not.toBeInTheDocument();
  });

  it('allows toggling between simple and cryptographic attestation', async () => {
    const { quest, currentUser } = createTestScenario('attestation');
    const user = userEvent.setup();
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // Initially should show simple attestation
    expect(screen.getByRole('button', { name: /Attest Completion/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Use Cryptographic Attestation/i })).toBeInTheDocument();

    // Toggle to cryptographic attestation
    await user.click(screen.getByRole('button', { name: /Use Cryptographic Attestation/i }));

    // Should now show the toggle back button
    expect(screen.getByRole('button', { name: /Use Simple Attestation/i })).toBeInTheDocument();
    
    // Should show cryptographic attestation component
    expect(screen.getByText('Cryptographic Attestation')).toBeInTheDocument();
  });

  it('does not render for quests in invalid states', () => {
    const { quest, currentUser } = createTestScenario('attestation');
    
    // Set quest to OPEN status
    quest.status = QuestStatus.OPEN;
    
    const { container } = render(
      <QuestAttestationForm
        questId={quest.questId}
        quest={quest}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // Component should return null for non-SUBMITTED/COMPLETE quests
    expect(container.firstChild).toBeNull();
  });

  it('fetches quest data if not provided', async () => {
    const { quest, currentUser } = createTestScenario('attestation');
    
    // Mock the API to return quest data
    vi.spyOn(api, 'getQuest').mockResolvedValue(quest);
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        currentUserId={currentUser.userId}
        onSuccess={mockOnSuccess}
      />
    );

    // Should show loading initially
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    // Wait for quest to load
    await waitFor(() => {
      expect(screen.getByText('Dual-Attestation Verification')).toBeInTheDocument();
    });

    // Verify API was called
    expect(api.getQuest).toHaveBeenCalledWith(quest.questId);
  });
});