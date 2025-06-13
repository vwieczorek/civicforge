import { test, expect } from '@playwright/test';
import { config } from '../src/config';

test.describe('Quest Attestation', () => {
  test.beforeEach(async ({ page }) => {
    // For attestation tests, we need a quest in SUBMITTED status
    // Mock the API to return a submitted quest
    await page.route(`${config.API_BASE_URL}/api/v1/quests/*`, route => {
      if (route.request().url().includes('/api/v1/quests/') && !route.request().url().includes('/attest')) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            questId: 'test-quest-123',
            title: 'Test Quest for Attestation',
            description: 'This quest needs attestation',
            status: 'SUBMITTED',
            creatorId: 'creator-123',
            performerId: 'performer-456',
            submissionText: 'Quest completed successfully!',
            rewardAmount: 100,
            rewardCurrency: 'XP',
          }),
        });
      } else {
        route.continue();
      }
    });

    // Navigate to the quest detail page
    await page.goto('/quests/test-quest-123');
  });

  test('should display attestation form for quest creator', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('h1');
    
    // Verify attestation UI is visible
    await expect(page.locator('text=/attest.*completion/i')).toBeVisible();
    await expect(page.locator('button:has-text("Attest")')).toBeVisible();
    
    // Verify submission details are shown
    await expect(page.locator('text=Quest completed successfully!')).toBeVisible();
  });

  test('should submit attestation without signature', async ({ page }) => {
    // Find and click attest button
    const attestButton = page.locator('button:has-text("Attest")');
    await attestButton.click();
    
    // If there's a modal, handle it
    const modalAttest = page.locator('button:has-text("Submit Attestation")');
    if (await modalAttest.isVisible({ timeout: 2000 })) {
      // Add optional notes
      const notesField = page.locator('textarea[name="notes"], textarea[placeholder*="notes"]');
      if (await notesField.isVisible()) {
        await notesField.fill('Work completed as requested.');
      }
      
      await modalAttest.click();
    }
    
    // Wait for success message
    await expect(page.locator('text=/attested|complete|success/i')).toBeVisible({ timeout: 10000 });
    
    // Verify quest status changed to COMPLETE
    await expect(page.locator('text=/status.*complete/i')).toBeVisible();
  });

  test('should handle wallet signature flow for attestation', async ({ page }) => {
    // Mock window.ethereum
    await page.addInitScript(() => {
      (window as any).ethereum = {
        request: async ({ method }: { method: string }) => {
          if (method === 'eth_requestAccounts') {
            return ['0x1234567890123456789012345678901234567890'];
          }
          if (method === 'personal_sign') {
            return '0xmocked_signature_123';
          }
          return null;
        },
        on: () => {},
        removeListener: () => {},
      };
    });

    // Click attest with signature option if available
    const signatureOption = page.locator('text=/sign.*chain/i');
    if (await signatureOption.isVisible()) {
      await signatureOption.click();
    }

    // Click attest button
    await page.locator('button:has-text("Attest")').click();
    
    // Handle signature flow
    const signButton = page.locator('button:has-text("Sign")');
    if (await signButton.isVisible()) {
      await signButton.click();
      
      // Wait for wallet interaction to complete
      await page.waitForTimeout(1000);
    }
    
    // Submit attestation
    const submitButton = page.locator('button:has-text("Submit Attestation")');
    if (await submitButton.isVisible()) {
      await submitButton.click();
    }
    
    // Verify success
    await expect(page.locator('text=/attested|complete|success/i')).toBeVisible({ timeout: 10000 });
  });

  test('should handle attestation errors gracefully (mocked)', async ({ page }) => {
    // Mock attestation failure
    await page.route(`${config.API_BASE_URL}/api/v1/quests/*/attest`, route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ 
          error: 'Invalid attestation',
          detail: 'You are not authorized to attest this quest' 
        }),
      });
    });
    
    // Try to attest
    await page.locator('button:has-text("Attest")').click();
    
    // Submit if modal appears
    const submitButton = page.locator('button:has-text("Submit Attestation")');
    if (await submitButton.isVisible({ timeout: 2000 })) {
      await submitButton.click();
    }
    
    // Verify error message
    await expect(page.locator('text=/not authorized|error|failed/i')).toBeVisible();
  });

  test('should prevent double attestation (mocked)', async ({ page }) => {
    // Mock quest that's already attested
    await page.route(`${config.API_BASE_URL}/api/v1/quests/*`, route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          questId: 'test-quest-123',
          title: 'Already Attested Quest',
          status: 'COMPLETE',
          attestations: [{
            userId: 'creator-123',
            attestedAt: new Date().toISOString(),
            role: 'creator'
          }],
        }),
      });
    });
    
    await page.reload();
    
    // Verify attestation button is not available
    await expect(page.locator('button:has-text("Attest")')).not.toBeVisible();
    
    // Verify completion status is shown
    await expect(page.locator('text=/complete|attested/i')).toBeVisible();
  });
});