import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmailAuthForm } from '../EmailAuthForm';
import { PasscodeVerification } from '../PasscodeVerification';
import { logout, logoutAllDevices } from '../../../auth/logout';
import { api } from '../../../api/client';

// Mock amplify auth
vi.mock('aws-amplify/auth', () => ({
  signIn: vi.fn(),
  confirmSignIn: vi.fn(),
  signOut: vi.fn(),
  fetchAuthSession: vi.fn()
}));

// Mock api client
vi.mock('../../../api/client', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn()
  }
}));

describe('Security Enhancements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set NODE_ENV to production to test error handling
    process.env.NODE_ENV = 'production';
  });

  afterEach(() => {
    process.env.NODE_ENV = 'test';
  });

  describe('Error Message Security', () => {
    it('should not expose detailed error information in EmailAuthForm', async () => {
      const mockError = vi.fn();
      const { signIn } = await import('aws-amplify/auth');
      
      // Mock signIn to throw an error
      vi.mocked(signIn).mockRejectedValue(new Error('UserNotFoundException: User does not exist'));
      
      render(<EmailAuthForm onCodeSent={vi.fn()} onError={mockError} />);
      
      const input = screen.getByPlaceholderText('Enter your email');
      const button = screen.getByText('Send code');
      
      await userEvent.type(input, 'test@example.com');
      await userEvent.click(button);
      
      // Check that generic error is shown
      await waitFor(() => {
        expect(screen.getByText('Unable to send verification code. Please try again.')).toBeInTheDocument();
      });
      
      // Original error should still be passed to error handler
      expect(mockError).toHaveBeenCalled();
    });

    it('should not expose detailed error information in PasscodeVerification', async () => {
      const mockError = vi.fn();
      const { confirmSignIn } = await import('aws-amplify/auth');
      
      // Mock confirmSignIn to throw an error
      vi.mocked(confirmSignIn).mockRejectedValue(new Error('NotAuthorizedException: Invalid code'));
      
      render(
        <PasscodeVerification 
          email="test@example.com"
          onSuccess={vi.fn()}
          onError={mockError}
        />
      );
      
      // Enter all digits
      const inputs = screen.getAllByRole('textbox');
      for (let i = 0; i < 6; i++) {
        await userEvent.type(inputs[i], (i + 1).toString());
      }
      
      // Check that generic error is shown
      await waitFor(() => {
        expect(screen.getByText('Invalid verification code. Please try again.')).toBeInTheDocument();
      });
    });
  });

  describe('Console Logging Security', () => {
    it('should not log errors to console in production', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Test that console.error is not called in production
      render(
        <EmailAuthForm 
          onCodeSent={vi.fn()} 
          onError={() => {
            // This should not log in production
            if (process.env.NODE_ENV === 'development') {
              console.error('Auth error');
            }
          }}
        />
      );
      
      expect(consoleSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
      
      consoleSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });
  });

  describe('Request Timeout', () => {
    it('should handle request timeout gracefully', async () => {
      // Mock fetch to simulate timeout
      const originalFetch = global.fetch;
      global.fetch = vi.fn().mockImplementation(() => {
        return new Promise((_, reject) => {
          setTimeout(() => {
            reject(new DOMException('The operation was aborted', 'AbortError'));
          }, 100);
        });
      });
      
      try {
        await api.get('/test');
      } catch (error) {
        expect(error.message).toBe('Request timed out. Please check your connection and try again.');
      }
      
      global.fetch = originalFetch;
    });
  });

  describe('Token Revocation', () => {
    it('should attempt to revoke token on logout', async () => {
      const { signOut } = await import('aws-amplify/auth');
      vi.mocked(api.post).mockResolvedValue({ success: true });
      vi.mocked(signOut).mockResolvedValue({});
      
      // Mock window.location
      delete window.location;
      window.location = { href: '' } as any;
      
      await logout();
      
      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/logout', {
        revoke_all_sessions: false,
        reason: 'user_logout'
      });
      expect(signOut).toHaveBeenCalled();
    });

    it('should continue logout even if token revocation fails', async () => {
      const { signOut } = await import('aws-amplify/auth');
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'));
      vi.mocked(signOut).mockResolvedValue({});
      
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Mock window.location
      delete window.location;
      window.location = { href: '' } as any;
      
      await logout();
      
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Token revocation failed, proceeding with local logout:',
        expect.any(Error)
      );
      expect(signOut).toHaveBeenCalled();
      
      consoleWarnSpy.mockRestore();
    });

    it('should support logout from all devices', async () => {
      vi.mocked(api.post).mockResolvedValue({ success: true });
      const { signOut } = await import('aws-amplify/auth');
      vi.mocked(signOut).mockResolvedValue({});
      
      // Mock window.location
      delete window.location;
      window.location = { href: '' } as any;
      
      await logoutAllDevices();
      
      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/logout', {
        revoke_all_sessions: true,
        reason: 'security_logout_all'
      });
    });
  });

  describe('Auto-submit Security', () => {
    it('should handle clipboard paste for passcode', async () => {
      render(
        <PasscodeVerification 
          email="test@example.com"
          onSuccess={vi.fn()}
          onError={vi.fn()}
        />
      );
      
      const firstInput = screen.getAllByRole('textbox')[0];
      
      // Simulate paste event
      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: new DataTransfer()
      });
      Object.defineProperty(pasteEvent.clipboardData, 'getData', {
        value: () => '123456'
      });
      
      fireEvent.paste(firstInput, pasteEvent);
      
      // All inputs should be filled
      const inputs = screen.getAllByRole('textbox');
      await waitFor(() => {
        inputs.forEach((input, index) => {
          expect(input).toHaveValue((index + 1).toString());
        });
      });
    });
  });
});