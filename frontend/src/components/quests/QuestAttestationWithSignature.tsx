import React, { useState } from 'react';
import { ethers } from 'ethers';

interface QuestAttestationWithSignatureProps {
  questId: string;
  userId: string;
  role: 'requestor' | 'performer';
  onAttest: (signature: string) => Promise<void>;
}

const QuestAttestationWithSignature: React.FC<QuestAttestationWithSignatureProps> = ({
  questId,
  userId,
  role,
  onAttest
}) => {
  const [isSigningInProgress, setIsSigningInProgress] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createAttestationMessage = (questId: string, userId: string, role: string): string => {
    // IMPORTANT: This must match the format in backend/src/signature.py EXACTLY
    return (
      `I am attesting to the completion of CivicForge Quest.\n` +
      `Quest ID: ${questId}\n` +
      `My User ID: ${userId}\n` +
      `My Role: ${role}`
    );
  };

  const handleSignAndAttest = async () => {
    setIsSigningInProgress(true);
    setError(null);

    try {
      // Check if MetaMask is installed
      if (!window.ethereum) {
        throw new Error('Please install MetaMask to sign attestations');
      }

      // Request account access
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      
      // Get the signer
      const signer = await provider.getSigner();
      
      // Create the message
      const message = createAttestationMessage(questId, userId, role);
      
      // Sign the message
      const signature = await signer.signMessage(message);
      
      // Send the attestation with signature
      await onAttest(signature);
      
    } catch (err: any) {
      console.error('Signing error:', err);
      setError(err.message || 'Failed to sign attestation');
    } finally {
      setIsSigningInProgress(false);
    }
  };

  return (
    <div className="attestation-container">
      <h3>Cryptographic Attestation</h3>
      <p>
        Sign this attestation with your wallet to create a cryptographically verifiable proof
        of quest completion.
      </p>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      <button
        onClick={handleSignAndAttest}
        disabled={isSigningInProgress}
        className="attest-button"
      >
        {isSigningInProgress ? 'Signing...' : 'Sign and Attest'}
      </button>
      
      <div className="signing-info">
        <small>
          This will prompt your wallet to sign a message. No transaction fees are required.
        </small>
      </div>
    </div>
  );
};

export default QuestAttestationWithSignature;

// Add TypeScript declaration for window.ethereum
declare global {
  interface Window {
    ethereum?: any;
  }
}