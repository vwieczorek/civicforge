import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Quest, QuestStatus } from '../api/types';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { useErrorHandler } from '../hooks/useErrorHandler';
import toast from 'react-hot-toast';
import QuestFilters, { FilterOptions } from '../components/quests/QuestFilters';

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
    </div>
  );
};

const QuestList: React.FC = () => {
  const [quests, setQuests] = useState<Quest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions>({
    search: '',
    status: '',
    sortBy: 'newest'
  });
  const { handleError } = useErrorHandler();
  const navigate = useNavigate();

  useEffect(() => {
    fetchQuests();
  }, []);

  const fetchQuests = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiClient.get<Quest[]>('/api/v1/quests');
      setQuests(response);
      toast.success('Quests loaded successfully');
    } catch (err) {
      const errorMessage = handleError(err, {
        fallbackMessage: 'Failed to load quests. Please try again later.'
      });
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter and sort quests - must be before conditional returns
  const filteredAndSortedQuests = useMemo(() => {
    let filtered = [...quests];
    
    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(quest => 
        quest.title.toLowerCase().includes(searchLower) ||
        quest.description.toLowerCase().includes(searchLower)
      );
    }
    
    // Apply status filter
    if (filters.status) {
      filtered = filtered.filter(quest => quest.status === filters.status);
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
      switch (filters.sortBy) {
        case 'newest':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'oldest':
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        case 'xp-high':
          return b.rewardXp - a.rewardXp;
        case 'xp-low':
          return a.rewardXp - b.rewardXp;
        case 'reputation-high':
          return b.rewardReputation - a.rewardReputation;
        case 'reputation-low':
          return a.rewardReputation - b.rewardReputation;
        default:
          return 0;
      }
    });
    
    return filtered;
  }, [quests, filters]);

  const openQuests = filteredAndSortedQuests.filter(q => q.status === QuestStatus.OPEN);
  const otherQuests = filteredAndSortedQuests.filter(q => q.status !== QuestStatus.OPEN);

  if (isLoading) {
    return (
      <div className="quest-list-container">
        <div className="page-header">
          <h1>Available Quests</h1>
          <p className="page-subtitle">
            Discover opportunities to contribute and earn rewards through peer-verified tasks
          </p>
        </div>
        <div className="quest-section">
          <h2>Loading...</h2>
          <div className="quest-grid">
            <LoadingSkeleton variant="card" count={3} />
          </div>
        </div>
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

  return (
    <div className="quest-list-container">
      <div className="page-header">
        <h1>Available Quests</h1>
        <p className="page-subtitle">
          Discover opportunities to contribute and earn rewards through peer-verified tasks
        </p>
      </div>

      <QuestFilters filters={filters} onFilterChange={setFilters} />

      {filteredAndSortedQuests.length === 0 ? (
        <div className="empty-state">
          <p>No quests found matching your filters.</p>
          {(filters.search || filters.status) && (
            <button 
              onClick={() => setFilters({ search: '', status: '', sortBy: 'newest' })} 
              className="clear-filters-button"
            >
              Clear Filters
            </button>
          )}
        </div>
      ) : openQuests.length > 0 ? (
        <div className="quest-section">
          <h2>Open Quests</h2>
          <div className="quest-grid">
            {openQuests.map(quest => (
              <div 
                key={quest.questId} 
                onClick={() => navigate(`/quests/${quest.questId}`)}
                style={{ cursor: 'pointer' }}
              >
                <QuestCard quest={quest} />
              </div>
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
              <div 
                key={quest.questId} 
                onClick={() => navigate(`/quests/${quest.questId}`)}
                style={{ cursor: 'pointer' }}
              >
                <QuestCard quest={quest} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestList;