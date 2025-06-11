import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../client'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock AWS Auth
vi.mock('aws-amplify', () => ({
  Auth: {
    currentSession: vi.fn(),
  },
}))

import { Auth } from 'aws-amplify'

describe('ApiClient', () => {
  const client = api
  
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Authentication', () => {
    it('should include auth header when user is authenticated', async () => {
      const mockToken = 'mock-jwt-token'
      const mockSession = {
        getIdToken: () => ({
          getJwtToken: () => mockToken,
        }),
      }
      
      ;(Auth.currentSession as any).mockResolvedValue(mockSession)
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

      await client.get('/test')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      )
    })

    it('should work without auth header when user is not authenticated', async () => {
      ;(Auth.currentSession as any).mockRejectedValue(new Error('Not authenticated'))
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

      await client.get('/test')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      )
    })
  })

  describe('HTTP Methods', () => {
    beforeEach(() => {
      ;(Auth.currentSession as any).mockRejectedValue(new Error('Not authenticated'))
    })

    it('should make GET requests', async () => {
      const mockResponse = { data: 'test' }
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.get('/test')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({ method: 'GET' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should make POST requests with body', async () => {
      const mockResponse = { success: true }
      const requestBody = { submissionText: 'Completed work' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.post('/quests/123/submit', requestBody)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/quests/123/submit'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(requestBody),
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('Error Handling', () => {
    beforeEach(() => {
      ;(Auth.currentSession as any).mockRejectedValue(new Error('Not authenticated'))
    })

    it('should throw error when response is not ok', async () => {
      const errorResponse = { detail: 'Quest not found' }
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve(errorResponse),
      })

      await expect(client.get('/quests/invalid')).rejects.toThrow('Quest not found')
    })

    it('should throw generic error when no detail provided', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({}),
      })

      await expect(client.get('/quests/invalid')).rejects.toThrow('API request failed')
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'))

      await expect(client.get('/test')).rejects.toThrow('Network error')
    })
  })

  describe('Quest API Methods', () => {
    beforeEach(() => {
      ;(Auth.currentSession as any).mockRejectedValue(new Error('Not authenticated'))
    })

    it('should fetch single quest', async () => {
      const mockQuest = { questId: '1', title: 'Quest 1', status: 'OPEN' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockQuest),
      })

      const result = await client.getQuest('1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/quests/1'),
        expect.objectContaining({ method: 'GET' })
      )
      expect(result).toEqual(mockQuest)
    })

    it('should claim quest', async () => {
      const mockResponse = { message: 'Quest claimed successfully' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.claimQuest('quest-123')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/quests/quest-123/claim'),
        expect.objectContaining({ method: 'POST' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should submit quest', async () => {
      const mockResponse = { message: 'Quest submitted successfully' }
      const submissionText = 'I completed this task'
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.submitQuest('quest-123', submissionText)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/quests/quest-123/submit'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ submissionText }),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should attest quest', async () => {
      const mockResponse = { message: 'Attestation added successfully' }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.attestQuest('quest-123')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/quests/quest-123/attest'),
        expect.objectContaining({ method: 'POST' })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should attest quest with signature', async () => {
      const mockResponse = { message: 'Attestation added successfully' }
      const signature = '0x123abc'
      const notes = 'Good work'
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.attestQuest('quest-123', signature, notes)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/quests/quest-123/attest'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ signature, notes }),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should dispute quest', async () => {
      const mockResponse = { message: 'Quest disputed successfully' }
      const reason = 'Work not completed as specified'
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await client.disputeQuest('quest-123', reason)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/quests/quest-123/dispute'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ reason }),
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })
})