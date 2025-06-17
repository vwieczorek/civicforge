import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getCurrentUser } from 'aws-amplify/auth';
import toast from 'react-hot-toast';
import { apiClient } from '../api/client';
import { Quest, QuestStatus } from '../api/types';
import QuestAttestationForm from '../components/quests/QuestAttestationForm';
import QuestAttestationDisplay from '../components/quests/QuestAttestationDisplay';
import WorkSubmissionModal from '../components/quests/WorkSubmissionModal';

const QuestDetail: React.FC = () => {
  const { questId } = useParams<{ questId: string }>();
  const navigate = useNavigate();
  const [quest, setQuest] = useState<Quest | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWorkSubmissionModal, setShowWorkSubmissionModal] = useState(false);

  useEffect(() => {
    if (questId) {
      fetchQuestAndUser();
    }
  }, [questId]);

  const fetchQuestAndUser = async () => {
    try {
      setIsLoading(true);
      
      // Fetch quest details
      const questData = await apiClient.get<Quest>(`/api/v1/quests/${questId}`);
      setQuest(questData);

      // Try to get current user ID
      try {
        const { userId } = await getCurrentUser();
        setCurrentUserId(userId);
      } catch {
        // User not authenticated, that's okay for viewing
        setCurrentUserId(null);
      }

      setError(null);
    } catch (err) {
      console.error('Failed to fetch quest details:', err);
      setError('Failed to load quest details. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClaimQuest = async () => {
    if (!currentUserId) {
      navigate('/login', { state: { from: location } });
      return;
    }

    try {
      await apiClient.post(`/api/v1/quests/${questId}/claim`, {});
      await fetchQuestAndUser(); // Refresh quest data
      toast.success('Quest claimed successfully!');
    } catch (err) {
      console.error('Failed to claim quest:', err);
      toast.error('Failed to claim quest. Please try again.');
    }
  };

  const handleSubmitWork = () => {
    setShowWorkSubmissionModal(true);
  };

  const handleWorkSubmission = async (submissionText: string) => {
    try {
      await apiClient.post(`/api/v1/quests/${questId}/submit`, {
        submissionText: submissionText
      });
      await fetchQuestAndUser(); // Refresh quest data
      setShowWorkSubmissionModal(false);
      toast.success('Work submitted successfully!');
    } catch (err) {
      console.error('Failed to submit work:', err);
      toast.error('Failed to submit work. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner">Loading quest details...</div>
      </div>
    );
  }

  if (error || !quest) {
    return (
      <div className="error-container">
        <p className="error-message">{error || 'Quest not found'}</p>
        <button onClick={() => navigate('/')} className="back-button">
          ← Back to Quests
        </button>
      </div>
    );
  }

  // Check if current user has already attested
  const currentUserAttestation = quest.attestations.find(
    att => att.user_id === currentUserId
  );

  // Check if user is the creator or performer
  const isCreator = currentUserId === quest.creatorId;
  const isPerformer = currentUserId === quest.performerId;
  const canClaim = quest.status === QuestStatus.OPEN && !isCreator && currentUserId;
  const canSubmit = quest.status === QuestStatus.CLAIMED && isPerformer;
  const canAttest = quest.status === QuestStatus.SUBMITTED && (isCreator || isPerformer);

  return (
    <div className="quest-detail-container">
      <div className="quest-header">
        <h1>{quest.title}</h1>
        <span className={`quest-status status-${quest.status.toLowerCase()}`}>
          {quest.status}
        </span>
      </div>

      <div className="quest-content">
        <section className="quest-description">
          <h2>Description</h2>
          <p>{quest.description}</p>
        </section>

        <section className="quest-rewards">
          <h2>Rewards</h2>
          <div className="reward-items">
            <div className="reward-item">
              <span className="reward-label">Experience Points:</span>
              <span className="reward-value">{quest.rewardXp} XP</span>
            </div>
            <div className="reward-item">
              <span className="reward-label">Reputation:</span>
              <span className="reward-value">+{quest.rewardReputation}</span>
            </div>
          </div>
        </section>

        {quest.submissionText && (
          <section className="quest-submission">
            <h2>Submitted Work</h2>
            <p>{quest.submissionText}</p>
          </section>
        )}

        <section className="quest-actions">
          {canClaim && (
            <button onClick={handleClaimQuest} className="primary-button">
              Claim Quest
            </button>
          )}

          {canSubmit && (
            <button onClick={handleSubmitWork} className="primary-button">
              Submit Completed Work
            </button>
          )}

          {canAttest && !currentUserAttestation && (
            <div className="attestation-section">
              <h2>Attestation Required</h2>
              <p>Please review the work and provide your attestation.</p>
              <QuestAttestationForm 
                questId={quest.questId}
                quest={quest}
                currentUserId={currentUserId}
                onSuccess={() => fetchQuestAndUser()}
              />
            </div>
          )}

          {currentUserAttestation && (
            <div className="attestation-section">
              <h2>Your Attestation</h2>
              <QuestAttestationDisplay attestation={currentUserAttestation} />
            </div>
          )}
        </section>

        <section className="quest-timeline">
          <h2>Timeline</h2>
          <ul className="timeline-list">
            <li>Created: {new Date(quest.createdAt).toLocaleDateString()}</li>
            {quest.claimedAt && (
              <li>Claimed: {new Date(quest.claimedAt).toLocaleDateString()}</li>
            )}
            {quest.submittedAt && (
              <li>Submitted: {new Date(quest.submittedAt).toLocaleDateString()}</li>
            )}
            {quest.completedAt && (
              <li>Completed: {new Date(quest.completedAt).toLocaleDateString()}</li>
            )}
          </ul>
        </section>
      </div>

      <button onClick={() => navigate('/')} className="back-button">
        ← Back to Quests
      </button>
      
      {quest && (
        <WorkSubmissionModal
          isOpen={showWorkSubmissionModal}
          onClose={() => setShowWorkSubmissionModal(false)}
          onSubmit={handleWorkSubmission}
          questTitle={quest.title}
        />
      )}
    </div>
  );
};

export default QuestDetail;