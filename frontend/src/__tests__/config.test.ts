import { describe, it, expect, vi } from 'vitest';
import { config } from '../config';

// The config is already mocked in test setup, so we just need to verify the mock
describe('config', () => {
  it('exports configuration with expected structure', () => {
    expect(config).toBeDefined();
    expect(config.aws).toBeDefined();
    expect(config.aws.region).toBe('us-east-1');
    expect(config.aws.userPoolId).toBe('test-pool');
    expect(config.aws.userPoolWebClientId).toBe('test-client');
    expect(config.api).toBeDefined();
    expect(config.api.url).toBe('http://localhost:3001');
    expect(config.isDevelopment).toBe(true);
  });

  it('has all required properties', () => {
    expect(config).toHaveProperty('aws');
    expect(config).toHaveProperty('api');
    expect(config).toHaveProperty('isDevelopment');
    expect(config.aws).toHaveProperty('region');
    expect(config.aws).toHaveProperty('userPoolId');
    expect(config.aws).toHaveProperty('userPoolWebClientId');
    expect(config.api).toHaveProperty('url');
  });
});