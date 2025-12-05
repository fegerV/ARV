import { test, expect } from '@playwright/test';

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
  });

  test('login page light theme', async ({ page }) => {
    await page.goto('/login');
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Take screenshot with masked sensitive fields
    await expect(page).toHaveScreenshot('login-light.png', {
      fullPage: true,
      mask: [page.locator('input[type="password"]')],
    });
  });

  test('login page dark theme', async ({ page }) => {
    await page.goto('/login');
    
    // Toggle to dark theme
    await page.keyboard.press('Control+T');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('login-dark.png', {
      fullPage: true,
      mask: [page.locator('input[type="password"]')],
    });
  });

  test('dashboard overview', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('dashboard-overview.png', {
      fullPage: true,
    });
  });

  test('companies list empty state', async ({ page }) => {
    await page.goto('/companies?filter=empty');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('companies-empty.png', {
      fullPage: true,
    });
  });

  test('companies table with data', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('companies-table.png', {
      fullPage: true,
    });
  });

  test('company creation form', async ({ page }) => {
    await page.goto('/companies/new');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('company-form.png', {
      fullPage: true,
    });
  });

  test('AR content detail page', async ({ page }) => {
    await page.goto('/ar-content/1');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('ar-content-detail.png', {
      fullPage: true,
    });
  });

  test('QR code modal', async ({ page }) => {
    await page.goto('/ar-content/1');
    await page.click('[data-testid="show-qr-code"]');
    
    await expect(page.locator('[data-testid="qr-code-modal"]')).toBeVisible();
    
    await expect(page.locator('[data-testid="qr-code-modal"]')).toHaveScreenshot('qr-code-modal.png');
  });

  test('video rotation scheduler', async ({ page }) => {
    await page.goto('/ar-content/1');
    await page.click('[data-testid="rotation-settings-button"]');
    
    await expect(page.locator('[data-testid="rotation-scheduler"]')).toBeVisible();
    
    await expect(page.locator('[data-testid="rotation-scheduler"]')).toHaveScreenshot('rotation-scheduler.png');
  });

  test('analytics dashboard', async ({ page }) => {
    await page.click('text=Аналитика');
    await page.waitForURL('**/analytics');
    await page.waitForLoadState('networkidle');
    
    // Wait for charts to render
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('analytics-dashboard.png', {
      fullPage: true,
    });
  });

  test('user menu dropdown', async ({ page }) => {
    await page.click('[data-testid="user-menu-button"]');
    
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    
    await expect(page.locator('[data-testid="user-menu"]')).toHaveScreenshot('user-menu.png');
  });

  test('mobile responsive - login', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('mobile-login.png', {
      fullPage: true,
    });
  });

  test('mobile responsive - dashboard', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('mobile-dashboard.png', {
      fullPage: true,
    });
  });

  test('tablet responsive - companies', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 }); // iPad
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('tablet-companies.png', {
      fullPage: true,
    });
  });
});
