import React from 'react';
import './LoadingSkeleton.css';

interface LoadingSkeletonProps {
  variant?: 'text' | 'card' | 'list' | 'profile';
  count?: number;
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ 
  variant = 'text', 
  count = 1 
}) => {
  const renderSkeleton = () => {
    switch (variant) {
      case 'card':
        return (
          <div className="skeleton-card">
            <div className="skeleton-header">
              <div className="skeleton-line skeleton-title"></div>
              <div className="skeleton-line skeleton-subtitle"></div>
            </div>
            <div className="skeleton-body">
              <div className="skeleton-line"></div>
              <div className="skeleton-line"></div>
              <div className="skeleton-line skeleton-short"></div>
            </div>
            <div className="skeleton-footer">
              <div className="skeleton-badge"></div>
              <div className="skeleton-badge"></div>
            </div>
          </div>
        );

      case 'list':
        return (
          <div className="skeleton-list-item">
            <div className="skeleton-line skeleton-title"></div>
            <div className="skeleton-line skeleton-short"></div>
          </div>
        );

      case 'profile':
        return (
          <div className="skeleton-profile">
            <div className="skeleton-avatar"></div>
            <div className="skeleton-profile-info">
              <div className="skeleton-line skeleton-name"></div>
              <div className="skeleton-line skeleton-email"></div>
            </div>
          </div>
        );

      case 'text':
      default:
        return <div className="skeleton-line"></div>;
    }
  };

  return (
    <div className="skeleton-container">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="skeleton-wrapper">
          {renderSkeleton()}
        </div>
      ))}
    </div>
  );
};

export default LoadingSkeleton;