import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { EmailAuthForm } from '../components/auth/EmailAuthForm';
import { PasscodeVerification } from '../components/auth/PasscodeVerification';
import './ModernLogin.css';

type AuthStep = 'email' | 'passcode';

const ModernLogin: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<AuthStep>('email');
  const [email, setEmail] = useState('');

  const handleCodeSent = (userEmail: string) => {
    setEmail(userEmail);
    setStep('passcode');
  };

  const handleSuccess = () => {
    // Navigate to the main app after successful authentication
    navigate('/quests');
  };

  const handleBack = () => {
    setStep('email');
    setEmail('');
  };

  return (
    <div className="modern-login-container">
      <div className="login-content">
        <div className="login-brand">
          <h1>CivicForge</h1>
          <p>Modern authentication for civic engagement</p>
        </div>

        <div className="login-card">
          {step === 'email' ? (
            <EmailAuthForm 
              onCodeSent={handleCodeSent}
              onError={(error) => {
                // Log errors securely without exposing details
                if (process.env.NODE_ENV === 'development') {
                  console.error('Auth error:', error);
                }
              }}
            />
          ) : (
            <PasscodeVerification
              email={email}
              onSuccess={handleSuccess}
              onBack={handleBack}
              onError={(error) => {
                // Log errors securely without exposing details
                if (process.env.NODE_ENV === 'development') {
                  console.error('Verification error:', error);
                }
              }}
            />
          )}
        </div>

        <div className="login-features">
          <div className="feature">
            <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
            </svg>
            <div>
              <h3>No passwords</h3>
              <p>Secure email codes only</p>
            </div>
          </div>
          
          <div className="feature">
            <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div>
              <h3>Quick access</h3>
              <p>Sign in with just your email</p>
            </div>
          </div>
          
          <div className="feature">
            <svg className="feature-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div>
              <h3>Enhanced security</h3>
              <p>Time-limited codes</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernLogin;