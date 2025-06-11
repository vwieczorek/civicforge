/**
 * Minimal API client for dual-attestation operations
 */

import { Auth } from 'aws-amplify';
import { Quest } from './types';
import { config } from '../config';

const API_ENDPOINT = config.api.url;

class ApiClient {
  private async getAuthHeader(): Promise<Record<string, string>> {
    try {
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      return { Authorization: `Bearer ${token}` };
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
      const error = await response.json();
      throw new Error(error.detail || 'API request failed');
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