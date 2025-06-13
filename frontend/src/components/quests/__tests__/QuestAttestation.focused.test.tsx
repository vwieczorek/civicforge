/**
 * Focused test for Quest Attestation flow
 * Tests the critical dual-attestation mechanism
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QuestAttestationForm from '../QuestAttestationForm';
import { createTestScenario } from '../../../test/mocks/factory';

// Mock ethers for wallet signing
const mockSignMessage = vi.fn();
const mockGetSigner = vi.fn(() => ({ signMessage: mockSignMessage }));
vi.mock('ethers', () => ({
  BrowserProvider: vi.fn(() => ({ getSigner: mockGetSigner })),
}));

// Mock window.ethereum
const mockEthereum = {
  request: vi.fn(),
};
global.window = { ...global.window, ethereum: mockEthereum };

describe('Quest Attestation - Critical Flow', () => {
  const { quest, attestationData } = createTestScenario('attestation');
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders attestation form with quest information', () => {
    render(
      <QuestAttestationForm
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText(/attest completion/i)).toBeInTheDocument();
    expect(screen.getByText(quest.title)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit attestation/i })).toBeInTheDocument();
  });

  it('allows attestation without wallet signature', async () => {
    const user = userEvent.setup();
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Add optional notes
    const notesInput = screen.getByPlaceholderText(/optional notes/i);
    await user.type(notesInput, 'Good work!');

    // Submit without signature
    await user.click(screen.getByRole('button', { name: /submit attestation/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        signature: null,
        notes: 'Good work!',
      });
    });
  });

  it('handles wallet signature flow for on-chain attestation', async () => {
    const user = userEvent.setup();
    
    // Setup successful wallet connection
    mockEthereum.request.mockResolvedValueOnce(['0x742d35Cc6634C0532925a3b844Bc9e7595f62149']);
    mockSignMessage.mockResolvedValueOnce(attestationData.signature);

    render(
      <QuestAttestationForm
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Click sign with wallet
    await user.click(screen.getByRole('button', { name: /sign with wallet/i }));

    // Should request wallet connection
    expect(mockEthereum.request).toHaveBeenCalledWith({ 
      method: 'eth_requestAccounts' 
    });

    // Wait for signature
    await waitFor(() => {
      expect(mockSignMessage).toHaveBeenCalledWith(
        expect.stringContaining(quest.questId)
      );
    });

    // Submit with signature
    await user.click(screen.getByRole('button', { name: /submit attestation/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        signature: attestationData.signature,
        notes: '',
      });
    });
  });

  it('handles wallet connection errors gracefully', async () => {
    const user = userEvent.setup();
    
    // Simulate user rejecting wallet connection
    mockEthereum.request.mockRejectedValueOnce(
      new Error('User rejected the request')
    );

    render(
      <QuestAttestationForm
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    await user.click(screen.getByRole('button', { name: /sign with wallet/i }));

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/failed to connect wallet/i)).toBeInTheDocument();
    });

    // Should still allow submission without signature
    await user.click(screen.getByRole('button', { name: /submit attestation/i }));
    
    expect(mockOnSubmit).toHaveBeenCalledWith({
      signature: null,
      notes: '',
    });
  });

  it('disables form during signature process', async () => {
    const user = userEvent.setup();
    
    // Setup wallet connection with delay
    mockEthereum.request.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve(['0x742d35Cc']), 100))
    );

    render(
      <QuestAttestationForm
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const signButton = screen.getByRole('button', { name: /sign with wallet/i });
    await user.click(signButton);

    // Button should be disabled during signing
    expect(signButton).toBeDisabled();
    expect(signButton).toHaveTextContent(/signing/i);
  });

  it('allows user to cancel attestation', async () => {
    const user = userEvent.setup();
    
    render(
      <QuestAttestationForm
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mockOnCancel).toHaveBeenCalled();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
});