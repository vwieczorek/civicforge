import { useCallback } from 'react';
import toast from 'react-hot-toast';

interface ErrorOptions {
  fallbackMessage?: string;
  showToast?: boolean;
  onError?: (error: Error) => void;
}

export const useErrorHandler = () => {
  const handleError = useCallback((error: unknown, options: ErrorOptions = {}) => {
    const {
      fallbackMessage = 'An unexpected error occurred',
      showToast = true,
      onError
    } = options;

    console.error('Error:', error);

    let message = fallbackMessage;

    if (error instanceof Error) {
      // Handle specific error types
      if (error.message.includes('Network')) {
        message = 'Network error. Please check your connection.';
      } else if (error.message.includes('Unauthorized')) {
        message = 'You need to sign in to perform this action.';
      } else if (error.message.includes('Forbidden')) {
        message = 'You don\'t have permission to perform this action.';
      } else if (error.message) {
        message = error.message;
      }
    } else if (typeof error === 'string') {
      message = error;
    }

    if (showToast) {
      toast.error(message);
    }

    if (onError && error instanceof Error) {
      onError(error);
    }

    return message;
  }, []);

  return { handleError };
};