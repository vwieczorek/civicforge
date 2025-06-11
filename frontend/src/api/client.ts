/**
 * Minimal API client for dual-attestation operations
 */

import { Auth } from 'aws-amplify';
import { Quest } from './types';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || '';

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

  async attestQuest(questId: string, notes?: string): Promise<Quest> {
    return this.request<Quest>(
      'POST',
      `/api/v1/quests/${questId}/attest`,
      { notes }
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