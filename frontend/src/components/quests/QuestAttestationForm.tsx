import React from 'react';
import { Quest, QuestStatus } from '../../api/types';
import { api } from '../../api/client';

interface Props {
  quest: Quest;
  currentUserId: string;
  onAttested: () => void;
}

export function QuestAttestationForm({ quest, currentUserId, onAttested }: Props) {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Determine user's role
  const isRequestor = quest.creatorId === currentUserId;
  const isPerformer = quest.performerId === currentUserId;
  const canAttest = (isRequestor || isPerformer) && quest.status === QuestStatus.SUBMITTED;
  
  // Check attestation status
  const attestations = quest.attestations || [];
  const hasRequestorAttested = attestations.some(a => a.role === 'requestor');
  const hasPerformerAttested = attestations.some(a => a.role === 'performer');
  const hasUserAttested = attestations.some(a => a.user_id === currentUserId);
  const isComplete = hasRequestorAttested && hasPerformerAttested;

  const handleAttest = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await api.attestQuest(quest.questId);
      onAttested();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to attest');
    } finally {
      setLoading(false);
    }
  };

  if (quest.status !== QuestStatus.SUBMITTED && quest.status !== QuestStatus.COMPLETE) {
    return null;
  }

  return (
    <div className="attestation-form">
      <h3>Dual-Attestation Verification</h3>
      
      <div className="attestation-info">
        <p>Both the requestor and performer must attest that the quest has been completed successfully.</p>
      </div>

      <div className="attestation-status">
        <h4>Attestation Progress</h4>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${attestations.length * 50}%` }}
          />
        </div>
        <p>{attestations.length} of 2 attestations</p>

        <div className="attestation-list">
          <div className={`attestation-item ${hasRequestorAttested ? 'attested' : ''}`}>
            <span className="icon">{hasRequestorAttested ? '✓' : '○'}</span>
            <span>Requestor {isRequestor ? '(You)' : ''}</span>
          </div>
          <div className={`attestation-item ${hasPerformerAttested ? 'attested' : ''}`}>
            <span className="icon">{hasPerformerAttested ? '✓' : '○'}</span>
            <span>Performer {isPerformer ? '(You)' : ''}</span>
          </div>
        </div>
      </div>

      {quest.submissionText && (
        <div className="submission-details">
          <h4>Submission</h4>
          <p>{quest.submissionText}</p>
        </div>
      )}

      {error && (
        <div className="error-message">{error}</div>
      )}

      {isComplete ? (
        <div className="success-message">
          Quest completed! The performer has been awarded {quest.rewardXp} XP and {quest.rewardReputation} reputation.
        </div>
      ) : canAttest && !hasUserAttested ? (
        <div className="attestation-action">
          <p className="warning">
            By attesting, you confirm that this quest has been completed according to the requirements.
          </p>
          <button 
            onClick={handleAttest} 
            disabled={loading}
            className="attest-button"
          >
            {loading ? 'Attesting...' : 'Attest Completion'}
          </button>
        </div>
      ) : hasUserAttested ? (
        <div className="info-message">
          You have attested. Waiting for the other party to attest.
        </div>
      ) : (
        <div className="info-message">
          You are not authorized to attest this quest.
        </div>
      )}
    </div>
  );
}