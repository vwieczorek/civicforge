import { test, expect } from '@playwright/test';
import { config } from '../src/config';

test.describe('Quest Discovery', () => {
  test.beforeEach(async ({ page }) => {
    // Start on the quests page
    await page.goto('/quests');
  });

  test('should display quest list from real backend', async ({ page }) => {
    // Wait for quest list to load
    await page.waitForSelector('.quest-card', { timeout: 10000 });
    
    // Verify quest cards are displayed
    const questCards = page.locator('.quest-card');
    await expect(questCards).toHaveCount.greaterThan(0);
    
    // Verify quest card contains expected elements
    const firstQuest = questCards.first();
    await expect(firstQuest.locator('.quest-title')).toBeVisible();
    await expect(firstQuest.locator('.quest-reward')).toBeVisible();
    await expect(firstQuest.locator('.quest-status')).toBeVisible();
  });

  test('should filter quests by status', async ({ page }) => {
    // Wait for initial load
    await page.waitForSelector('.quest-card');
    
    // Click on status filter (if implemented)
    const openFilter = page.locator('button:has-text("Open")');
    if (await openFilter.isVisible()) {
      await openFilter.click();
      
      // Verify only open quests are shown
      const questStatuses = page.locator('.quest-status');
      const count = await questStatuses.count();
      
      for (let i = 0; i < count; i++) {
        await expect(questStatuses.nth(i)).toContainText(/open/i);
      }
    }
  });

  test('should navigate to quest detail on click', async ({ page }) => {
    // Wait for quest list to load
    await page.waitForSelector('.quest-card');
    
    // Get first quest title for verification
    const firstQuestTitle = await page.locator('.quest-card .quest-title').first().textContent();
    
    // Click on first quest
    await page.locator('.quest-card').first().click();
    
    // Verify navigation to detail page
    await expect(page).toHaveURL(/\/quests\/[a-zA-Z0-9-]+/);
    
    // Verify quest title is displayed on detail page
    await expect(page.locator('h1')).toContainText(firstQuestTitle || '');
  });

  test('should handle empty quest list gracefully (mocked)', async ({ page }) => {
    // Mock empty quest list response
    await page.route(`${config.API_BASE_URL}/api/v1/quests`, route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ quests: [] }),
      });
    });
    
    // Reload to trigger mocked response
    await page.reload();
    
    // Verify empty state is shown
    await expect(page.locator('text=No quests available')).toBeVisible();
  });

  test('should handle API errors gracefully (mocked)', async ({ page }) => {
    // Mock API error
    await page.route(`${config.API_BASE_URL}/api/v1/quests`, route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });
    
    // Reload to trigger error
    await page.reload();
    
    // Verify error message is shown
    await expect(page.locator('text=/error|failed|sorry/i')).toBeVisible();
  });
});