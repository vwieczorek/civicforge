import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright-auth-state.json';

setup('authenticate', async ({ page }) => {
  // Use test credentials from environment variables
  const username = process.env.E2E_TEST_USERNAME || 'test@civicforge.local';
  const password = process.env.E2E_TEST_PASSWORD || 'TestPassword123!';

  // Navigate to the app
  await page.goto('/');
  
  // Wait for Amplify UI authenticator to load
  await page.waitForSelector('[data-amplify-authenticator]', { timeout: 10000 });
  
  // Fill in credentials
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);
  
  // Submit login form
  await page.click('button[type="submit"]');
  
  // Wait for successful authentication
  // Look for the sign out button as indicator of successful login
  await expect(page.locator('text=Sign out')).toBeVisible({ timeout: 10000 });
  
  // Save authentication state
  await page.context().storageState({ path: authFile });
});