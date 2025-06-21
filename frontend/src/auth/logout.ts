import { signOut } from 'aws-amplify/auth';
import { api } from '../api/client';

interface LogoutOptions {
  revokeAllSessions?: boolean;
  reason?: string;
}

/**
 * Logout user and revoke their tokens
 * 
 * @param options - Logout options
 * @returns Promise that resolves when logout is complete
 */
export async function logout(options: LogoutOptions = {}): Promise<void> {
  try {
    // First, try to revoke the token on the server
    // This will fail if the backend doesn't support token revocation yet
    try {
      await api.post('/api/v1/auth/logout', {
        revoke_all_sessions: options.revokeAllSessions || false,
        reason: options.reason || 'user_logout'
      });
    } catch (error) {
      // Log but don't fail the logout if revocation fails
      console.warn('Token revocation failed, proceeding with local logout:', error);
    }

    // Then sign out from Amplify (clears local session)
    await signOut();
    
    // Clear any local storage items
    clearLocalSession();
    
    // Redirect to login page
    window.location.href = '/login';
  } catch (error) {
    console.error('Logout failed:', error);
    
    // Even if logout fails, clear local session
    clearLocalSession();
    
    // Force redirect to login
    window.location.href = '/login';
  }
}

/**
 * Clear all local session data
 */
function clearLocalSession(): void {
  // Clear any app-specific storage
  localStorage.removeItem('civicforge_session');
  sessionStorage.clear();
  
  // Clear any cached data
  // This is where you'd clear any Redux store, React Query cache, etc.
}

/**
 * Logout user from all devices
 * Used when account may be compromised
 */
export async function logoutAllDevices(): Promise<void> {
  return logout({
    revokeAllSessions: true,
    reason: 'security_logout_all'
  });
}