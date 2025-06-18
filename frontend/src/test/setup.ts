// Add fetch polyfill at the very top
import { fetch, Headers, Request, Response } from 'undici'

global.fetch = fetch as any
global.Headers = Headers as any
global.Request = Request as any
global.Response = Response as any

import '@testing-library/jest-dom'
import { vi, beforeAll, afterEach, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { server } from '../mocks/server'

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

// Clean up after the tests are finished
afterAll(() => server.close())

// Mock config to avoid environment variable requirements
vi.mock('../config', () => ({
  config: {
    api: {
      url: 'http://localhost:3001',
    },
    aws: {
      region: 'us-east-1',
      userPoolId: 'test-pool',
      userPoolWebClientId: 'test-client',
    },
    isDevelopment: true,
  },
}))

// Mock the top-level Amplify object for configuration if needed
vi.mock('aws-amplify', async () => {
  const actual = await vi.importActual('aws-amplify');
  return {
    ...actual,
    Amplify: {
      ...(actual.Amplify || {}),
      configure: vi.fn(),
    },
  };
});

// Mock the auth module specifically, as it's imported directly
vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({}),
  getCurrentUser: vi.fn().mockResolvedValue({ 
    userId: 'user-123', // Corresponds to defaultUser in MSW handlers
    username: 'testuser' 
  }),
  signOut: vi.fn().mockResolvedValue(undefined),
}))

// Mock react-hot-toast to prevent errors in tests
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
  Toaster: () => null,
}))

// Mock ethers
vi.mock('ethers', () => ({
  BrowserProvider: vi.fn(() => ({
    getSigner: vi.fn(() => ({
      signMessage: vi.fn(),
      getAddress: vi.fn(() => '0x742d35Cc6634C0532925a3b844Bc9e7595f62149'),
    })),
  })),
  parseEther: vi.fn(() => '1000000000000000000'),
  formatEther: vi.fn(() => '1.0'),
}))

// Setup global window.ethereum
Object.defineProperty(window, 'ethereum', {
  value: {
    request: vi.fn(),
  },
  writable: true,
})