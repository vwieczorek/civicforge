import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../client'
import { server } from '../../mocks/server'
import { http, HttpResponse } from 'msw'
import { config } from '../../config'

// Mock AWS Auth
vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn(),
}))

import { fetchAuthSession } from 'aws-amplify/auth'

describe('ApiClient', () => {
  const client = api
  
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Authentication', () => {
    it('should include auth header when user is authenticated', async () => {
      const mockToken = 'mock-jwt-token'
      const mockSession = {
        tokens: {
          idToken: {
            toString: () => mockToken,
          },
        },
      }
      
      ;(fetchAuthSession as any).mockResolvedValue(mockSession)
      
      // Add a one-time handler to verify the auth header
      let capturedHeaders: any = null
      server.use(
        http.get(`${config.api.url}/test-auth`, ({ request }) => {
          capturedHeaders = Object.fromEntries(request.headers.entries())
          return HttpResponse.json({ success: true })
        })
      )

      await client.get('/test-auth')

      expect(capturedHeaders).toBeTruthy()
      expect(capturedHeaders.authorization).toBe(`Bearer ${mockToken}`)
    })

    it('should work without auth header when user is not authenticated', async () => {
      ;(fetchAuthSession as any).mockResolvedValue({})
      
      let capturedHeaders: any = null
      server.use(
        http.get(`${config.api.url}/test-no-auth`, ({ request }) => {
          capturedHeaders = Object.fromEntries(request.headers.entries())
          return HttpResponse.json({ success: true })
        })
      )

      await client.get('/test-no-auth')

      expect(capturedHeaders).toBeTruthy()
      expect(capturedHeaders.authorization).toBeUndefined()
    })
  })

  describe('HTTP Methods', () => {
    it('should make GET requests', async () => {
      // The /test endpoint is already handled by MSW
      const result = await client.get('/test')
      expect(result).toEqual({ success: true })
    })

    it('should make POST requests with body', async () => {
      const testData = { name: 'test', value: 123 }
      const result = await client.post('/test', testData)
      
      expect(result).toEqual({ ...testData, success: true })
    })
  })

  describe('Error Handling', () => {
    it('should throw error when response is not ok', async () => {
      await expect(client.get('/error/404')).rejects.toThrow('API request failed')
    })

    it('should throw generic error when no detail provided', async () => {
      server.use(
        http.get(`${config.api.url}/error/generic`, () => {
          return HttpResponse.json({}, { status: 400 })
        })
      )

      await expect(client.get('/error/generic')).rejects.toThrow('API request failed')
    })

    it('should handle network errors', async () => {
      server.use(
        http.get(`${config.api.url}/network-error`, () => {
          throw new Error('Network error')
        })
      )

      await expect(client.get('/network-error')).rejects.toThrow()
    })
  })

  describe('Quest API Methods', () => {
    it('should fetch single quest', async () => {
      const quest = await client.getQuest('quest-123')
      expect(quest).toMatchObject({
        questId: 'quest-123'
      })
    })

    it('should claim quest', async () => {
      const result = await client.claimQuest('quest-123')
      expect(result).toMatchObject({
        questId: 'quest-123',
        status: 'CLAIMED'
      })
    })

    it('should submit quest', async () => {
      const submissionText = 'My submission'
      const result = await client.submitQuest('quest-123', submissionText)
      
      expect(result).toMatchObject({
        questId: 'quest-123',
        status: 'SUBMITTED'
      })
    })

    it('should attest quest', async () => {
      const result = await client.attestQuest('quest-123')
      
      expect(result).toMatchObject({
        questId: 'quest-123',
        status: 'COMPLETE'
      })
    })

    it('should attest quest with signature', async () => {
      const signature = '0x123456789'
      const result = await client.attestQuest('quest-123', signature)
      
      expect(result).toMatchObject({
        questId: 'quest-123',
        status: 'COMPLETE',
        attestations: expect.arrayContaining([
          expect.objectContaining({
            signature
          })
        ])
      })
    })

    it('should dispute quest', async () => {
      const reason = 'Invalid submission'
      const result = await client.disputeQuest('quest-123', reason)
      
      expect(result).toMatchObject({
        questId: 'quest-123',
        status: 'DISPUTED'
      })
    })

    // Note: deleteQuest method doesn't exist in the current API client
  })
})