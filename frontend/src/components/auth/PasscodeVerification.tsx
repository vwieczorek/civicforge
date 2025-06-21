import React, { useState, useRef, useEffect } from 'react';
import { confirmSignIn, signIn } from 'aws-amplify/auth';
import './PasscodeVerification.css';

interface PasscodeVerificationProps {
  email: string;
  onSuccess: () => void;
  onError?: (error: Error) => void;
  onBack?: () => void;
}

export const PasscodeVerification: React.FC<PasscodeVerificationProps> = ({
  email,
  onSuccess,
  onError,
  onBack
}) => {
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    // Focus first input on mount
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (index: number, value: string) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    // Auto-advance to next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all digits entered
    if (value && index === 5 && newCode.every(digit => digit)) {
      handleSubmit(newCode.join(''));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    // Handle backspace
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').trim();
    
    // Only accept 6 digits
    if (/^\d{6}$/.test(pastedData)) {
      const digits = pastedData.split('');
      setCode(digits);
      inputRefs.current[5]?.focus();
      handleSubmit(pastedData);
    }
  };

  const handleSubmit = async (passcode?: string) => {
    const fullCode = passcode || code.join('');
    
    if (fullCode.length !== 6) {
      setError('Please enter all 6 digits');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const { isSignedIn } = await confirmSignIn({
        challengeResponse: fullCode
      });

      if (isSignedIn) {
        onSuccess();
      }
    } catch (err) {
      // Use generic error message to avoid information disclosure
      setError('Invalid verification code. Please try again.');
      onError?.(err as Error);
      
      // Clear code on error
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setSuccessMessage('');
    setCode(['', '', '', '', '', '']);
    setIsLoading(true);
    
    try {
      // Initiate auth again to resend code
      await signIn({
        username: email,
        options: {
          authFlowType: 'CUSTOM_WITHOUT_SRP'
        }
      });
      
      // Show success message
      setSuccessMessage(`New code sent to ${email}. Please check your email.`);
      inputRefs.current[0]?.focus();
    } catch (err) {
      // Use generic error message
      setError('Unable to send verification code. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="passcode-verification">
      <div className="verification-header">
        <h2>Check your email</h2>
        <p>We sent a code to <strong>{email}</strong></p>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="success-message" role="status">
          {successMessage}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
        <div className="passcode-inputs">
          {code.map((digit, index) => (
            <input
              key={index}
              ref={el => inputRefs.current[index] = el}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={index === 0 ? handlePaste : undefined}
              disabled={isLoading}
              className="passcode-input"
              aria-label={`Digit ${index + 1}`}
              autoComplete={index === 0 ? "one-time-code" : "off"}
            />
          ))}
        </div>

        <button
          type="submit"
          disabled={isLoading || code.some(d => !d)}
          className="verify-button"
        >
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              Verifying...
            </>
          ) : (
            'Verify code'
          )}
        </button>
      </form>

      <div className="verification-footer">
        <button
          type="button"
          onClick={handleResend}
          disabled={isLoading}
          className="link-button"
        >
          Send new code
        </button>
        
        {onBack && (
          <>
            <span className="separator">•</span>
            <button
              type="button"
              onClick={onBack}
              disabled={isLoading}
              className="link-button"
            >
              Use different email
            </button>
          </>
        )}
      </div>

      <p className="security-note">
        <svg className="icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
        Code expires in 5 minutes
      </p>
    </div>
  );
};