import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { Amplify } from 'aws-amplify';
import { Auth } from 'aws-amplify';
import { config } from './config';
import './App.css';

// Configure Amplify using centralized config
const awsConfig = config.aws;

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: awsConfig.userPoolId || '',
      userPoolClientId: awsConfig.userPoolWebClientId || '',
    }
  }
});

const Header: React.FC = () => {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);

  React.useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      await Auth.getCurrentUser();
      setIsAuthenticated(true);
    } catch {
      setIsAuthenticated(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await Auth.signOut();
      setIsAuthenticated(false);
      navigate('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <header className="app-header">
      <div className="header-content">
        <Link to="/" className="logo">CivicForge</Link>
        <nav className="nav-links">
          <Link to="/">Browse Quests</Link>
          {isAuthenticated && (
            <>
              <Link to="/create-quest">Create Quest</Link>
              <Link to="/profile">My Profile</Link>
            </>
          )}
        </nav>
        <div className="auth-section">
          {isAuthenticated ? (
            <button onClick={handleSignOut} className="auth-button">Sign Out</button>
          ) : (
            <Link to="/login" className="auth-button">Sign In</Link>
          )}
        </div>
      </div>
    </header>
  );
};

const App: React.FC = () => {
  return (
    <div className="app">
      <Header />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default App;