/**
 * Visual Regression Tests - UI Components
 * Проверка визуального соответствия компонентов
 */

import { test, expect } from '@playwright/test';

test.describe('Visual Regression: Components', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
  });

  test('dashboard page - light theme', async ({ page }) => {
    // Set light theme
    await page.evaluate(() => {
      localStorage.setItem('vertex-ar-theme', JSON.stringify({
        state: { mode: 'light' },
        version: 0
      }));
    });
    await page.reload();
    
    // Wait for page to stabilize
    await page.waitForLoadState('networkidle');
    
    // Take screenshot
    await expect(page).toHaveScreenshot('dashboard-light.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('dashboard page - dark theme', async ({ page }) => {
    // Set dark theme
    await page.evaluate(() => {
      localStorage.setItem('vertex-ar-theme', JSON.stringify({
        state: { mode: 'dark' },
        version: 0
      }));
    });
    await page.reload();
    
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('dashboard-dark.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('KPI cards snapshot', async ({ page }) => {
    const kpiCard = page.locator('[data-testid="kpi-card"]').first();
    
    await expect(kpiCard).toHaveScreenshot('kpi-card.png', {
      animations: 'disabled',
    });
  });

  test('sidebar navigation', async ({ page }) => {
    const sidebar = page.locator('[data-testid="sidebar-nav"]');
    
    await expect(sidebar).toHaveScreenshot('sidebar-nav.png', {
      animations: 'disabled',
    });
  });

  test('top bar with user menu', async ({ page }) => {
    const topBar = page.locator('[data-testid="top-bar"]');
    
    await expect(topBar).toHaveScreenshot('top-bar.png', {
      animations: 'disabled',
    });
  });

  test('companies list table', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    await page.waitForLoadState('networkidle');
    
    const table = page.locator('[data-testid="companies-table"]');
    
    await expect(table).toHaveScreenshot('companies-table.png', {
      animations: 'disabled',
    });
  });

  test('company form', async ({ page }) => {
    await page.click('text=Компании');
    await page.click('text=Новая компания');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('company-form.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('AR content card', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.waitForLoadState('networkidle');
    
    const contentCard = page.locator('[data-testid="ar-content-card"]').first();
    
    if (await contentCard.isVisible()) {
      await expect(contentCard).toHaveScreenshot('ar-content-card.png', {
        animations: 'disabled',
      });
    }
  });

  test('status badges', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.waitForLoadState('networkidle');
    
    // Ready status
    const readyBadge = page.locator('[data-status="ready"]').first();
    if (await readyBadge.isVisible()) {
      await expect(readyBadge).toHaveScreenshot('badge-ready.png');
    }
    
    // Processing status
    const processingBadge = page.locator('[data-status="processing"]').first();
    if (await processingBadge.isVisible()) {
      await expect(processingBadge).toHaveScreenshot('badge-processing.png');
    }
  });

  test('empty state component', async ({ page }) => {
    // Navigate to empty list
    await page.click('text=Компании');
    await page.click('text=Новая компания');
    
    // Go to projects (should be empty for new company)
    const emptyState = page.locator('[data-testid="empty-state"]');
    
    if (await emptyState.isVisible()) {
      await expect(emptyState).toHaveScreenshot('empty-state.png', {
        animations: 'disabled',
      });
    }
  });

  test('loading spinner', async ({ page }) => {
    // Trigger loading state
    await page.click('text=Аналитика');
    
    const spinner = page.locator('[data-testid="loading-spinner"]');
    
    if (await spinner.isVisible({ timeout: 1000 })) {
      await expect(spinner).toHaveScreenshot('loading-spinner.png');
    }
  });

  test('modal dialog', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForLoadState('networkidle');
    
    // Open delete confirmation
    await page.click('[data-testid="delete-company-button"]:first-child');
    
    const dialog = page.locator('[data-testid="confirm-dialog"]');
    await expect(dialog).toBeVisible();
    
    await expect(dialog).toHaveScreenshot('confirm-dialog.png', {
      animations: 'disabled',
    });
  });

  test('notification toast', async ({ page }) => {
    // Trigger notification
    await page.click('text=Компании');
    await page.click('text=Новая компания');
    await page.fill('[data-testid="company-name"]', 'Test');
    await page.click('[data-testid="create-company-button"]');
    
    const toast = page.locator('[data-testid="toast-notification"]');
    
    if (await toast.isVisible({ timeout: 2000 })) {
      await expect(toast).toHaveScreenshot('toast-notification.png');
    }
  });

  test('QR code display', async ({ page }) => {
    await page.click('text=AR Контент');
    await page.click('[data-testid="ar-content-row"]:first-child');
    
    const qrCode = page.locator('[data-testid="qr-code-card"]');
    
    if (await qrCode.isVisible()) {
      await expect(qrCode).toHaveScreenshot('qr-code-card.png', {
        animations: 'disabled',
      });
    }
  });

  test('analytics charts', async ({ page }) => {
    await page.click('text=Аналитика');
    await page.waitForLoadState('networkidle');
    
    // Wait for chart rendering
    await page.waitForTimeout(2000);
    
    const chart = page.locator('[data-testid="views-chart"]').first();
    
    if (await chart.isVisible()) {
      await expect(chart).toHaveScreenshot('analytics-chart.png', {
        animations: 'disabled',
      });
    }
  });
});

test.describe('Visual Regression: Responsive Design', () => {
  test('mobile viewport - dashboard', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('dashboard-mobile.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('tablet viewport - companies list', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    await page.click('text=Компании');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('companies-tablet.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('wide screen - dashboard', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('dashboard-wide.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});
