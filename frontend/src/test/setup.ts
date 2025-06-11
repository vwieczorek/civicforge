import '@testing-library/jest-dom'

// Mock config to avoid environment variable requirements
vi.mock('../config', () => ({
  config: {
    api: {
      url: 'http://localhost:3001',
    },
    cognito: {
      region: 'us-east-1',
      userPoolId: 'test-pool',
      userPoolClientId: 'test-client',
    },
  },
}))

// Mock AWS Amplify
vi.mock('aws-amplify', () => ({
  Amplify: {
    configure: vi.fn(),
  },
  Auth: {
    currentSession: vi.fn(),
    getCurrentUser: vi.fn(),
    signOut: vi.fn(),
  },
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