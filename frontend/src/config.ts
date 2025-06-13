/**
 * Centralized configuration for the CivicForge frontend
 * Handles environment variables and provides a single source of truth
 */

// Get the raw environment variables from Vite
const env = import.meta.env;

// Validate critical variables and throw an error if they are missing
if (!env.VITE_USER_POOL_ID || !env.VITE_USER_POOL_CLIENT_ID) {
  throw new Error("Missing critical AWS Cognito environment variables.");
}

// Create and export a clean, typed configuration object
export const config = {
  aws: {
    region: env.VITE_AWS_REGION || 'us-east-1',
    userPoolId: env.VITE_USER_POOL_ID,
    userPoolWebClientId: env.VITE_USER_POOL_CLIENT_ID,
  },
  api: {
    url: env.VITE_API_URL || '',
  },
  // Environment-specific flags
  isDevelopment: env.MODE === 'development',
};

// Quick check for the API URL in development
if (config.isDevelopment && !config.api.url) {
  console.warn("VITE_API_URL is not set. API calls may fail.");
}