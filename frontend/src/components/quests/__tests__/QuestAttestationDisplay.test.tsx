import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import QuestAttestationDisplay from '../QuestAttestationDisplay';
import type { Attestation } from '../../../api/types';

describe('QuestAttestationDisplay', () => {
  const mockAttestation: Attestation = {
    user_id: 'user-123',
    role: 'requestor',
    attested_at: '2024-01-01T10:00:00Z',
  };

  const mockAttestationWithSignature: Attestation = {
    user_id: 'user-456',
    role: 'performer',
    attested_at: '2024-01-01T11:00:00Z',
    signature: '0x1234567890abcdef',
  };

  it('displays attestation role', () => {
    render(<QuestAttestationDisplay attestation={mockAttestation} />);

    expect(screen.getByText('Role:')).toBeInTheDocument();
    expect(screen.getByText('requestor')).toBeInTheDocument();
  });

  it('displays attestation timestamp', () => {
    render(<QuestAttestationDisplay attestation={mockAttestation} />);

    expect(screen.getByText('Attested:')).toBeInTheDocument();
    // Check for date display (format may vary by locale)
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it('shows signature when available', () => {
    render(<QuestAttestationDisplay attestation={mockAttestationWithSignature} />);

    expect(screen.getByText('Signature:')).toBeInTheDocument();
    // The component shows first 10 chars and last 8 chars
    expect(screen.getByText(/0x12345678...90abcdef/)).toBeInTheDocument();
  });

  it('shows verification status', () => {
    render(<QuestAttestationDisplay attestation={mockAttestation} />);

    expect(screen.getByText('✅ Cryptographically verified')).toBeInTheDocument();
  });

  it('does not show signature field when signature is not provided', () => {
    render(<QuestAttestationDisplay attestation={mockAttestation} />);

    expect(screen.queryByText('Signature:')).not.toBeInTheDocument();
  });
});