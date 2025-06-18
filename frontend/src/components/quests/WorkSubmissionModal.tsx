import React, { useState } from 'react';
import './WorkSubmissionModal.css';

interface WorkSubmissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (submissionText: string) => void;
  questTitle: string;
}

const WorkSubmissionModal: React.FC<WorkSubmissionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  questTitle
}) => {
  const [submissionText, setSubmissionText] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!submissionText.trim()) {
      setError('Please describe your completed work');
      return;
    }
    
    if (submissionText.trim().length < 10) {
      setError('Please provide at least 10 characters describing your work');
      return;
    }
    
    onSubmit(submissionText.trim());
    setSubmissionText('');
    setError('');
  };

  const handleClose = () => {
    setSubmissionText('');
    setError('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Submit Completed Work</h2>
          <button className="modal-close" onClick={handleClose} aria-label="Close">
            ×
          </button>
        </div>
        
        <div className="modal-body">
          <p className="quest-title">For quest: <strong>{questTitle}</strong></p>
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="submission-text">
                Describe your completed work
                <span className="required">*</span>
              </label>
              <textarea
                id="submission-text"
                value={submissionText}
                onChange={(e) => {
                  setSubmissionText(e.target.value);
                  setError('');
                }}
                placeholder="Explain what you did to complete this quest..."
                rows={6}
                maxLength={1000}
                required
              />
              <div className="character-count">
                {submissionText.length}/1000 characters
              </div>
              {error && <span className="field-error">{error}</span>}
            </div>
            
            <div className="modal-actions">
              <button type="button" onClick={handleClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Submit Work
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default WorkSubmissionModal;