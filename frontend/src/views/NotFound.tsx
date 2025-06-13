import React from 'react';
import { Link } from 'react-router-dom';
import './NotFound.css';

const NotFound: React.FC = () => {
  return (
    <div className="not-found-container">
      <div className="not-found-content">
        <h1 className="not-found-title">404</h1>
        <h2 className="not-found-subtitle">Page Not Found</h2>
        <p className="not-found-message">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="not-found-actions">
          <Link to="/" className="not-found-link">
            Browse Quests
          </Link>
          <Link to="/create-quest" className="not-found-link secondary">
            Create a Quest
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFound;