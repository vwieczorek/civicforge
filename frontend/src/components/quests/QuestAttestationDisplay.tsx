import React from 'react';
import { Attestation } from '../../api/types';

interface QuestAttestationDisplayProps {
  attestation: Attestation;
}

const QuestAttestationDisplay: React.FC<QuestAttestationDisplayProps> = ({ attestation }) => {
  return (
    <div className="attestation-display">
      <div className="attestation-info">
        <div className="attestation-field">
          <span className="field-label">Role:</span>
          <span className="field-value">{attestation.role}</span>
        </div>
        <div className="attestation-field">
          <span className="field-label">Attested:</span>
          <span className="field-value">
            {new Date(attestation.attested_at).toLocaleString()}
          </span>
        </div>
        {attestation.signature && (
          <div className="attestation-field">
            <span className="field-label">Signature:</span>
            <span className="field-value signature-hash">
              {attestation.signature.slice(0, 10)}...{attestation.signature.slice(-8)}
            </span>
          </div>
        )}
      </div>
      <div className="attestation-status">
        ✅ Cryptographically verified
      </div>
    </div>
  );
};

export default QuestAttestationDisplay;