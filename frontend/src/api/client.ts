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
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        return { Authorization: `Bearer ${token}` };
      }
      return {};
    } catch {
      return {};
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<T> {
    const headers = await this.getAuthHeader();
    
    const response = await fetch(`${API_ENDPOINT}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let errorMessage = 'API request failed';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch {
        // If we can't parse JSON, use status text
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return response.json();
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