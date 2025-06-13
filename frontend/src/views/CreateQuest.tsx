import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';

interface QuestFormData {
  title: string;
  description: string;
  rewardXp: number;
  rewardReputation: number;
}

const CreateQuest: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<QuestFormData>({
    title: '',
    description: '',
    rewardXp: 100,
    rewardReputation: 10,
  });
  const [errors, setErrors] = useState<Partial<Record<keyof QuestFormData, string>>>({});

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof QuestFormData, string>> = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    } else if (formData.title.length < 5) {
      newErrors.title = 'Title must be at least 5 characters';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.length < 20) {
      newErrors.description = 'Description must be at least 20 characters';
    }

    if (formData.rewardXp < 10) {
      newErrors.rewardXp = 'XP reward must be at least 10';
    }

    if (formData.rewardReputation < 1) {
      newErrors.rewardReputation = 'Reputation reward must be at least 1';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'rewardXp' || name === 'rewardReputation' 
        ? parseInt(value) || 0 
        : value
    }));
    // Clear error for this field when user starts typing
    if (errors[name as keyof QuestFormData]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setIsSubmitting(true);
      const response = await apiClient.post<{ questId: string }>('/api/v1/quests', formData);
      
      // Navigate to the newly created quest
      navigate(`/quests/${response.questId}`);
    } catch (err) {
      console.error('Failed to create quest:', err);
      alert('Failed to create quest. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="create-quest-container">
      <div className="page-header">
        <h1>Create a New Quest</h1>
        <p className="page-subtitle">
          Define a task that needs to be completed and verified by the community
        </p>
      </div>

      <form onSubmit={handleSubmit} className="quest-form">
        <div className="form-group">
          <label htmlFor="title">Quest Title</label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            placeholder="Enter a clear, descriptive title"
            className={errors.title ? 'error' : ''}
            maxLength={100}
          />
          {errors.title && <span className="error-message">{errors.title}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Provide detailed instructions and requirements for completing this quest"
            rows={6}
            className={errors.description ? 'error' : ''}
            maxLength={1000}
          />
          {errors.description && (
            <span className="error-message">{errors.description}</span>
          )}
          <span className="character-count">
            {formData.description.length}/1000 characters
          </span>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="rewardXp">Experience Points (XP)</label>
            <input
              type="number"
              id="rewardXp"
              name="rewardXp"
              value={formData.rewardXp.toString()}
              onChange={handleInputChange}
              min="10"
              max="10000"
              className={errors.rewardXp ? 'error' : ''}
            />
            {errors.rewardXp && (
              <span className="error-message">{errors.rewardXp}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="rewardReputation">Reputation Points</label>
            <input
              type="number"
              id="rewardReputation"
              name="rewardReputation"
              value={formData.rewardReputation.toString()}
              onChange={handleInputChange}
              min="1"
              max="100"
              className={errors.rewardReputation ? 'error' : ''}
            />
            {errors.rewardReputation && (
              <span className="error-message">{errors.rewardReputation}</span>
            )}
          </div>
        </div>

        <div className="form-info">
          <h3>How it works:</h3>
          <ul>
            <li>Once created, your quest will be available for others to claim</li>
            <li>When someone claims it, they'll have time to complete the task</li>
            <li>After submission, both parties must attest to successful completion</li>
            <li>Rewards are distributed only after dual attestation</li>
          </ul>
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="secondary-button"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="primary-button"
          >
            {isSubmitting ? 'Creating...' : 'Create Quest'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateQuest;