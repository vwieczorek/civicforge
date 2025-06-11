import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Quest, QuestStatus } from '../api/types';

const QuestCard: React.FC<{ quest: Quest }> = ({ quest }) => {
  const getStatusBadgeClass = (status: QuestStatus) => {
    switch (status) {
      case QuestStatus.OPEN:
        return 'status-open';
      case QuestStatus.CLAIMED:
        return 'status-claimed';
      case QuestStatus.COMPLETE:
        return 'status-complete';
      default:
        return 'status-default';
    }
  };

  return (
    <div className="quest-card">
      <div className="quest-card-header">
        <h3 className="quest-title">{quest.title}</h3>
        <span className={`quest-status ${getStatusBadgeClass(quest.status)}`}>
          {quest.status}
        </span>
      </div>
      <p className="quest-description">{quest.description}</p>
      <div className="quest-rewards">
        <span className="reward-item">
          <strong>XP:</strong> {quest.rewardXp}
        </span>
        <span className="reward-item">
          <strong>Reputation:</strong> {quest.rewardReputation}
        </span>
      </div>
      <Link to={`/quests/${quest.questId}`} className="quest-link">
        View Details →
      </Link>
    </div>
  );
};

const QuestList: React.FC = () => {
  const [quests, setQuests] = useState<Quest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchQuests();
  }, []);

  const fetchQuests = async () => {
    try {
      setIsLoading(true);
      // For now, we'll need to add this method to the API client
      const response = await apiClient.get<Quest[]>('/api/v1/quests');
      setQuests(response);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch quests:', err);
      setError('Failed to load quests. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner">Loading quests...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="error-message">{error}</p>
        <button onClick={fetchQuests} className="retry-button">
          Try Again
        </button>
      </div>
    );
  }

  const openQuests = quests.filter(q => q.status === QuestStatus.OPEN);
  const otherQuests = quests.filter(q => q.status !== QuestStatus.OPEN);

  return (
    <div className="quest-list-container">
      <div className="page-header">
        <h1>Available Quests</h1>
        <p className="page-subtitle">
          Discover opportunities to contribute and earn rewards through peer-verified tasks
        </p>
      </div>

      {openQuests.length > 0 ? (
        <div className="quest-section">
          <h2>Open Quests</h2>
          <div className="quest-grid">
            {openQuests.map(quest => (
              <QuestCard key={quest.questId} quest={quest} />
            ))}
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <p>No open quests available at the moment.</p>
          <Link to="/create-quest" className="cta-button">
            Create a Quest
          </Link>
        </div>
      )}

      {otherQuests.length > 0 && (
        <div className="quest-section">
          <h2>Recent Activity</h2>
          <div className="quest-grid">
            {otherQuests.map(quest => (
              <QuestCard key={quest.questId} quest={quest} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestList;