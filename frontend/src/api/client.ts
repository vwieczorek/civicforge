/**
 * Minimal API client for dual-attestation operations
 */

import { fetchAuthSession } from 'aws-amplify/auth';
import { Quest } from './types';
import { config } from '../config';

const API_ENDPOINT = config.api.url;

class ApiClient {
  private async getAuthHeader(): Promise<Record<string, string>> {
    try {
      const session = await fetchAuthSession();
      // Try access token first, fallback to ID token if not available
      const accessToken = session.tokens?.accessToken?.toString();
      const idToken = session.tokens?.idToken?.toString();
      const token = accessToken || idToken;
      
      if (token) {
        // Only log token type in development
        if (!accessToken && idToken && process.env.NODE_ENV === 'development') {
          console.warn('Using ID token as fallback - access token not available');
        }
        return { Authorization: `Bearer ${token}` };
      }
      return {};
    } catch (error) {
      console.error('Failed to fetch auth session:', error);
      return {};
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any,
    options: { timeout?: number } = {}
  ): Promise<T> {
    const headers = await this.getAuthHeader();
    
    // Create an AbortController for timeout
    const controller = new AbortController();
    const timeoutMs = options.timeout || 30000; // Default 30 second timeout
    
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, timeoutMs);
    
    try {
      const response = await fetch(`${API_ENDPOINT}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

    if (!response.ok) {
      // Use generic error messages based on status code
      let errorMessage = 'Request failed. Please try again.';
      
      if (response.status === 401) {
        errorMessage = 'Please sign in to continue.';
      } else if (response.status === 403) {
        errorMessage = 'You do not have permission to perform this action.';
      } else if (response.status === 404) {
        errorMessage = 'The requested resource was not found.';
      } else if (response.status >= 500) {
        errorMessage = 'A server error occurred. Please try again later.';
      }
      
      // Only log detailed errors in development
      if (process.env.NODE_ENV === 'development') {
        try {
          const error = await response.json();
          console.error('API Error:', error);
        } catch {
          console.error('API Error:', response.statusText);
        }
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
    } catch (error) {
      // Clear timeout on error
      clearTimeout(timeoutId);
      
      // Handle timeout specifically
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timed out. Please check your connection and try again.');
      }
      
      // Re-throw other errors
      throw error;
    } finally {
      // Always clear the timeout
      clearTimeout(timeoutId);
    }
  }

  // Generic methods for reuse
  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  async post<T>(path: string, body?: any): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  // Quest operations
  async getQuest(questId: string): Promise<Quest> {
    return this.request<Quest>('GET', `/api/v1/quests/${questId}`);
  }

  async claimQuest(questId: string): Promise<Quest> {
    return this.request<Quest>('POST', `/api/v1/quests/${questId}/claim`);
  }

  async submitQuest(
    questId: string, 
    submissionText: string
  ): Promise<Quest> {
    return this.request<Quest>(
      'POST', 
      `/api/v1/quests/${questId}/submit`,
      { submissionText }
    );
  }

  async attestQuest(questId: string, signature?: string, notes?: string): Promise<Quest> {
    return this.request<Quest>(
      'POST',
      `/api/v1/quests/${questId}/attest`,
      { signature, notes }
    );
  }

  async disputeQuest(questId: string, reason: string): Promise<Quest> {
    return this.request<Quest>(
      'POST',
      `/api/v1/quests/${questId}/dispute`,
      { reason }
    );
  }
}

export const api = new ApiClient();
export const apiClient = api; // alias for compatibility