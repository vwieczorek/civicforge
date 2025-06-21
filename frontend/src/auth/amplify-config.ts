import { Amplify } from 'aws-amplify';
import { config } from '../config';

// Configure Amplify for custom authentication flow
export const configureAmplify = () => {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.aws.userPoolId || '',
        userPoolClientId: config.aws.userPoolWebClientId || '',
        signUpVerificationMethod: 'code',
        loginWith: {
          email: true,
          username: false,
          phone: false
        }
      }
    }
  });
};

// Custom auth helpers for email passcode flow
export const authHelpers = {
  // Format email for consistent handling
  normalizeEmail: (email: string): string => {
    return email.toLowerCase().trim();
  },

  // Validate email format
  isValidEmail: (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  // Get remaining time for passcode (5 minutes)
  getPasscodeExpiryTime: (): Date => {
    const expiry = new Date();
    expiry.setMinutes(expiry.getMinutes() + 5);
    return expiry;
  }
};