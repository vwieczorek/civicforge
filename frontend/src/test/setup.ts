import '@testing-library/jest-dom'
import { vi } from 'vitest'
import { server } from '../mocks/server'

// Establish API mocking before all tests
beforeAll(() => server.listen())

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => server.resetHandlers())

// Clean up after the tests are finished
afterAll(() => server.close())

// Mock config to avoid environment variable requirements
vi.mock('../config', () => ({
  config: {
    API_BASE_URL: 'http://localhost:3001',
    api: {
      url: 'http://localhost:3001',
    },
    cognito: {
      region: 'us-east-1',
      userPoolId: 'test-pool',
      userPoolClientId: 'test-client',
    },
    aws: {
      userPoolId: 'test-pool',
      userPoolWebClientId: 'test-client',
    },
  },
}))

// Mock the top-level Amplify object for configuration if needed
vi.mock('aws-amplify', () => ({
  Amplify: {
    configure: vi.fn(),
  },
}));

// Mock the auth module specifically, as it's imported directly
vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn(),
  getCurrentUser: vi.fn(),
  signOut: vi.fn(),
}))

// Mock ethers
vi.mock('ethers', () => ({
  BrowserProvider: vi.fn(),
  parseEther: vi.fn(),
  formatEther: vi.fn(),
}))