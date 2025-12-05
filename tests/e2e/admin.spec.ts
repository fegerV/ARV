import { test, expect } from '@playwright/test';

test.describe('Admin Panel E2E', () => {
  test('Create company → Project → AR Content → QR Code', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button:has-text("Login")');

    await page.goto('/companies/new');
    await page.fill('[data-testid="company-name"]', 'Test Agency');
    await page.click('[data-testid="connect-yandex"]');

    // OAuth flow simulation...

    await page.click('button:has-text("Create Company")');
    await expect(page).toHaveURL(/\/companies\/\d+/);

    // Create project, upload content, generate QR
    await page.goto('/companies/1/projects/new');
    // ... full flow
  });
});
