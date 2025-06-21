import React, { useState } from 'react';
import { signIn } from 'aws-amplify/auth';
import './EmailAuthForm.css';

interface EmailAuthFormProps {
  onCodeSent: (email: string) => void;
  onError?: (error: Error) => void;
}

export const EmailAuthForm: React.FC<EmailAuthFormProps> = ({ onCodeSent, onError }) => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setIsLoading(true);

    try {
      // Initiate custom auth challenge
      const { nextStep } = await signIn({
        username: email,
        options: {
          authFlowType: 'CUSTOM_WITHOUT_SRP'
        }
      });

      if (nextStep.signInStep === 'CONFIRM_SIGN_IN_WITH_CUSTOM_CHALLENGE') {
        onCodeSent(email);
      }
    } catch (err) {
      // Use generic error message to avoid information disclosure
      setError('Unable to send verification code. Please try again.');
      onError?.(err as Error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="email-auth-form">
      <form onSubmit={handleSubmit}>
        <div className="form-header">
          <h2>Sign in with email</h2>
          <p>We'll send you a secure code</p>
        </div>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="email" className="visually-hidden">
            Email address
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
            disabled={isLoading}
            autoComplete="email"
            autoFocus
            className="email-input"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !email}
          className="submit-button"
        >
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              Sending code...
            </>
          ) : (
            'Send code'
          )}
        </button>

        <div className="form-footer">
          <p className="security-note">
            <svg className="icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
            </svg>
            No passwords needed. We'll email you a secure code.
          </p>
        </div>
      </form>
    </div>
  );
};