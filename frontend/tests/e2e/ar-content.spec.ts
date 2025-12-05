import { test, expect } from '@playwright/test';

test.describe('AR Content Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
  });

  test('complete AR content creation flow', async ({ page }) => {
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Select company
    await page.click('[data-testid="company-row"]:first-child');
    
    // Navigate to projects
    await page.click('text=Проекты');
    
    // Select project
    await page.click('[data-testid="project-row"]:first-child');
    
    // Navigate to AR content
    await page.click('text=AR Контент');
    
    // Create new AR content
    await page.click('text=Новый AR контент');
    
    // Upload portrait image
    const portraitInput = page.locator('input[type="file"][data-testid="portrait-upload"]');
    await portraitInput.setInputFiles('./tests/fixtures/test-portrait.jpg');
    
    // Wait for upload
    await expect(page.getByText(/загружено/i)).toBeVisible({ timeout: 10000 });
    
    // Generate marker
    await page.click('[data-testid="generate-marker-button"]');
    
    // Wait for marker generation
    await expect(page.getByText(/маркер создается/i)).toBeVisible();
    await expect(page.getByText(/маркер готов/i)).toBeVisible({ timeout: 30000 });
    
    // Upload video
    const videoInput = page.locator('input[type="file"][data-testid="video-upload"]');
    await videoInput.setInputFiles('./tests/fixtures/test-video.mp4');
    
    // Wait for video processing
    await expect(page.getByText(/видео загружено/i)).toBeVisible({ timeout: 20000 });
    
    // Set video as default
    await page.click('[data-testid="set-default-video"]');
    
    // Activate AR content
    await page.click('[data-testid="activate-ar-content"]');
    
    // Verify activation
    await expect(page.locator('[data-testid="ar-status-active"]')).toBeVisible();
    
    // Download QR code
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="download-qr-code"]');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.png$/);
  });

  test('video rotation schedule setup', async ({ page }) => {
    // Navigate to AR content
    await page.click('text=AR Контент');
    await page.click('[data-testid="ar-content-row"]:first-child');
    
    // Open rotation settings
    await page.click('[data-testid="rotation-settings-button"]');
    
    // Set daily rotation
    await page.selectOption('[data-testid="rotation-mode"]', 'daily_cycle');
    
    // Set day 1 video
    await page.selectOption('[data-testid="day-1-video"]', { index: 1 });
    
    // Set day 2 video
    await page.selectOption('[data-testid="day-2-video"]', { index: 2 });
    
    // Save rotation
    await page.click('[data-testid="save-rotation-button"]');
    
    // Verify save
    await expect(page.getByText(/расписание сохранено/i)).toBeVisible();
  });

  test('date-specific video schedule', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.click('[data-testid="ar-content-row"]:first-child');
    
    // Open rotation settings
    await page.click('[data-testid="rotation-settings-button"]');
    
    // Switch to date-specific
    await page.selectOption('[data-testid="rotation-mode"]', 'date_specific');
    
    // Add date rule
    await page.click('[data-testid="add-date-rule"]');
    
    // Set date range
    await page.fill('[data-testid="start-date"]', '2025-12-20');
    await page.fill('[data-testid="end-date"]', '2025-12-31');
    
    // Select video
    await page.selectOption('[data-testid="date-rule-video"]', { index: 1 });
    
    // Save
    await page.click('[data-testid="save-rotation-button"]');
    
    await expect(page.getByText(/правило создано/i)).toBeVisible();
  });

  test('view AR content analytics', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.click('[data-testid="ar-content-row"]:first-child');
    
    // Navigate to analytics tab
    await page.click('text=Аналитика');
    
    // Verify analytics widgets
    await expect(page.locator('[data-testid="total-views"]')).toBeVisible();
    await expect(page.locator('[data-testid="avg-fps"]')).toBeVisible();
    await expect(page.locator('[data-testid="device-breakdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="views-chart"]')).toBeVisible();
  });

  test('copy permanent link', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.click('[data-testid="ar-content-row"]:first-child');
    
    // Click copy link button
    await page.click('[data-testid="copy-permanent-link"]');
    
    // Verify copied message
    await expect(page.getByText(/ссылка скопирована/i)).toBeVisible();
    
    // Verify clipboard (requires clipboard permissions in Playwright)
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toMatch(/\/ar\//);
  });

  test('deactivate AR content', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.click('[data-testid="ar-content-row"]:first-child');
    
    // Click deactivate button
    await page.click('[data-testid="deactivate-ar-content"]');
    
    // Confirm
    await page.click('button:has-text("Деактивировать")');
    
    // Verify status change
    await expect(page.locator('[data-testid="ar-status-inactive"]')).toBeVisible();
    await expect(page.getByText(/контент деактивирован/i)).toBeVisible();
  });
});
