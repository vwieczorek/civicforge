import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright-auth-state.json';

setup('authenticate', async ({ page }) => {
  // Use test credentials from environment variables
  const username = process.env.E2E_TEST_USERNAME || 'test@civicforge.local';
  const password = process.env.E2E_TEST_PASSWORD || 'TestPassword123!';

  // Navigate to the app
  await page.goto('/');
  
  // Wait for the custom login page to load by looking for its heading
  await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible({ timeout: 10000 });
  
  // Fill in credentials using the correct labels from the custom form
  await page.getByLabel('Email').fill(username);
  await page.getByLabel('Password').fill(password);
  
  // Submit login form by finding the button with its specific text
  await page.getByRole('button', { name: 'Sign In' }).click();
  
  // Wait for successful authentication
  // Look for the sign out button as indicator of successful login
  await expect(page.locator('text=Sign out')).toBeVisible({ timeout: 10000 });
  
  // Save authentication state
  await page.context().storageState({ path: authFile });
});