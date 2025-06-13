import { test, expect } from '@playwright/test';
import { config } from '../src/config';

test.describe('Quest Interaction', () => {
  let questId: string;

  test.beforeEach(async ({ page }) => {
    // Navigate to quests and select first available quest
    await page.goto('/quests');
    await page.waitForSelector('.quest-card');
    
    // Extract quest ID from first quest's link
    const questLink = await page.locator('.quest-card').first().getAttribute('href');
    questId = questLink?.split('/').pop() || 'test-quest';
    
    // Navigate to quest detail
    await page.locator('.quest-card').first().click();
    await page.waitForURL(/\/quests\/[a-zA-Z0-9-]+/);
  });

  test('should display quest details', async ({ page }) => {
    // Verify all quest details are displayed
    await expect(page.locator('h1')).toBeVisible(); // Quest title
    await expect(page.locator('text=/description/i')).toBeVisible();
    await expect(page.locator('text=/reward/i')).toBeVisible();
    await expect(page.locator('text=/xp.*[0-9]+/i')).toBeVisible();
    
    // Verify action buttons based on quest status
    const claimButton = page.locator('button:has-text("Claim Quest")');
    const submitButton = page.locator('button:has-text("Submit")');
    
    // At least one action should be available
    const hasClaimButton = await claimButton.isVisible();
    const hasSubmitButton = await submitButton.isVisible();
    expect(hasClaimButton || hasSubmitButton).toBeTruthy();
  });

  test('should claim quest successfully', async ({ page }) => {
    // Look for claim button (only visible for unclaimed quests)
    const claimButton = page.locator('button:has-text("Claim Quest")');
    
    if (await claimButton.isVisible()) {
      // Click claim button
      await claimButton.click();
      
      // Wait for success message or status change
      await expect(page.locator('text=/claimed|success/i')).toBeVisible({ timeout: 10000 });
      
      // Verify submit button appears after claiming
      await expect(page.locator('button:has-text("Submit")')).toBeVisible();
    }
  });

  test('should submit quest completion', async ({ page }) => {
    // First ensure quest is claimed (skip if already claimed)
    const claimButton = page.locator('button:has-text("Claim Quest")');
    if (await claimButton.isVisible()) {
      await claimButton.click();
      await page.waitForTimeout(1000); // Wait for claim to process
    }
    
    // Look for submit button
    const submitButton = page.locator('button:has-text("Submit")');
    
    if (await submitButton.isVisible()) {
      // Fill submission text if required
      const submissionField = page.locator('textarea[name="submission"], textarea[placeholder*="submission"]');
      if (await submissionField.isVisible()) {
        await submissionField.fill('I have completed this quest successfully!');
      }
      
      // Submit the quest
      await submitButton.click();
      
      // Wait for success indication
      await expect(page.locator('text=/submitted|success|pending.*attestation/i')).toBeVisible({ timeout: 10000 });
    }
  });

  test('should handle quest already claimed error (mocked)', async ({ page }) => {
    // Mock API to return "already claimed" error
    await page.route(`${config.API_BASE_URL}/api/v1/quests/${questId}/claim`, route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ 
          error: 'Quest already claimed',
          detail: 'This quest has already been claimed by another user' 
        }),
      });
    });
    
    const claimButton = page.locator('button:has-text("Claim Quest")');
    if (await claimButton.isVisible()) {
      await claimButton.click();
      
      // Verify error message is displayed
      await expect(page.locator('text=/already claimed/i')).toBeVisible();
    }
  });

  test('should handle network errors gracefully (mocked)', async ({ page }) => {
    // Mock network failure
    await page.route(`${config.API_BASE_URL}/api/v1/quests/${questId}/submit`, route => {
      route.abort('failed');
    });
    
    // Try to submit (assuming quest is already claimed)
    const submitButton = page.locator('button:has-text("Submit")');
    if (await submitButton.isVisible()) {
      await submitButton.click();
      
      // Verify error handling
      await expect(page.locator('text=/error|failed|try again/i')).toBeVisible();
    }
  });
});