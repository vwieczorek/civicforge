import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getCurrentUser } from 'aws-amplify/auth';
import { apiClient } from '../api/client';
import { User, Quest, QuestStatus } from '../api/types';

interface UserProfileData extends User {
  createdQuests: Quest[];
  performedQuests: Quest[];
}

const UserProfile: React.FC = () => {
  const [profile, setProfile] = useState<UserProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'created' | 'performed'>('created');

  useEffect(() => {
    fetchUserProfile();
  }, []);

  const fetchUserProfile = async () => {
    try {
      setIsLoading(true);
      
      // Get current user
      const { userId } = await getCurrentUser();

      // Fetch user profile data
      const profileData = await apiClient.get<UserProfileData>(`/api/v1/users/${userId}`);
      setProfile(profileData);
      
      setError(null);
    } catch (err) {
      console.error('Failed to fetch user profile:', err);
      setError('Failed to load profile. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  const getQuestStatusColor = (status: QuestStatus) => {
    switch (status) {
      case QuestStatus.COMPLETE:
        return 'success';
      case QuestStatus.OPEN:
        return 'info';
      case QuestStatus.CLAIMED:
        return 'warning';
      case QuestStatus.DISPUTED:
        return 'danger';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner">Loading profile...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="error-container">
        <p className="error-message">{error || 'Profile not found'}</p>
        <button onClick={fetchUserProfile} className="retry-button">
          Try Again
        </button>
      </div>
    );
  }

  const questsToShow = activeTab === 'created' 
    ? profile.createdQuests 
    : profile.performedQuests;

  return (
    <div className="user-profile-container">
      <div className="profile-header">
        <div className="profile-info">
          <h1>{profile.username}</h1>
          <p className="member-since">
            Member since {new Date(profile.createdAt).toLocaleDateString()}
          </p>
        </div>

        <div className="profile-stats">
          <div className="stat-card">
            <div className="stat-value">{profile.reputation}</div>
            <div className="stat-label">Reputation</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{profile.experience}</div>
            <div className="stat-label">Experience</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{profile.createdQuests.length}</div>
            <div className="stat-label">Quests Created</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{profile.performedQuests.length}</div>
            <div className="stat-label">Quests Completed</div>
          </div>
        </div>
      </div>

      <div className="profile-content">
        <div className="tab-navigation">
          <button
            className={`tab-button ${activeTab === 'created' ? 'active' : ''}`}
            onClick={() => setActiveTab('created')}
          >
            Created Quests ({profile.createdQuests.length})
          </button>
          <button
            className={`tab-button ${activeTab === 'performed' ? 'active' : ''}`}
            onClick={() => setActiveTab('performed')}
          >
            Performed Quests ({profile.performedQuests.length})
          </button>
        </div>

        <div className="quest-list">
          {questsToShow.length === 0 ? (
            <div className="empty-state">
              <p>
                {activeTab === 'created' 
                  ? "You haven't created any quests yet." 
                  : "You haven't completed any quests yet."}
              </p>
              <Link 
                to={activeTab === 'created' ? '/create-quest' : '/'} 
                className="cta-button"
              >
                {activeTab === 'created' ? 'Create Your First Quest' : 'Browse Available Quests'}
              </Link>
            </div>
          ) : (
            <div className="quest-table">
              {questsToShow.map(quest => (
                <div key={quest.questId} className="quest-row">
                  <div className="quest-info">
                    <Link to={`/quests/${quest.questId}`} className="quest-title">
                      {quest.title}
                    </Link>
                    <span className={`quest-status status-${getQuestStatusColor(quest.status)}`}>
                      {quest.status}
                    </span>
                  </div>
                  <div className="quest-meta">
                    <span className="quest-date">
                      {new Date(quest.createdAt).toLocaleDateString()}
                    </span>
                    <span className="quest-rewards">
                      {quest.rewardXp} XP • +{quest.rewardReputation} Rep
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserProfile;