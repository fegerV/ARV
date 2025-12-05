/**
 * E2E Tests: Dashboard & Navigation
 * Критические пользовательские сценарии для навигации и dashboard
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboard & Global Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
  });

  test('dashboard displays all KPI cards', async ({ page }) => {
    // Verify all 8 KPI cards are visible
    await expect(page.locator('[data-testid="kpi-card"]')).toHaveCount(8);
    
    // Verify key metrics
    await expect(page.getByText(/Всего просмотров/i)).toBeVisible();
    await expect(page.getByText(/Уникальных сессий/i)).toBeVisible();
    await expect(page.getByText(/Активного контента/i)).toBeVisible();
    await expect(page.getByText(/Компаний/i)).toBeVisible();
  });

  test('sidebar navigation works correctly', async ({ page }) => {
    // Navigate through all main sections
    await page.click('text=Компании');
    await expect(page).toHaveURL(/\/companies/);
    
    await page.click('text=Проекты');
    await expect(page).toHaveURL(/\/projects/);
    
    await page.click('text=AR Контент');
    await expect(page).toHaveURL(/\/ar-content/);
    
    await page.click('text=Аналитика');
    await expect(page).toHaveURL(/\/analytics/);
    
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('breadcrumbs navigation', async ({ page }) => {
    // Navigate deep
    await page.click('text=Компании');
    await page.click('[data-testid="company-row"]:first-child');
    
    // Verify breadcrumbs
    await expect(page.locator('[data-testid="breadcrumb-companies"]')).toBeVisible();
    await expect(page.locator('[data-testid="breadcrumb-current"]')).toBeVisible();
    
    // Click breadcrumb to go back
    await page.click('[data-testid="breadcrumb-companies"]');
    await expect(page).toHaveURL(/\/companies$/);
  });

  test('global search functionality', async ({ page }) => {
    // Open global search
    await page.keyboard.press('Control+K');
    
    // Search dialog should open
    await expect(page.locator('[data-testid="global-search"]')).toBeVisible();
    
    // Type search query
    await page.fill('[data-testid="search-input"]', 'Test Company');
    
    // Wait for results
    await expect(page.locator('[data-testid="search-result"]').first()).toBeVisible();
    
    // Click result
    await page.click('[data-testid="search-result"]:first-child');
    
    // Should navigate to result
    await expect(page).toHaveURL(/\/companies\/\d+/);
  });

  test('theme toggle keyboard shortcut', async ({ page }) => {
    // Get initial theme
    const initialTheme = await page.locator('html').getAttribute('data-theme');
    
    // Toggle theme with Ctrl+T
    await page.keyboard.press('Control+T');
    
    // Wait for theme change
    await page.waitForTimeout(500);
    
    // Verify theme changed
    const newTheme = await page.locator('html').getAttribute('data-theme');
    expect(newTheme).not.toBe(initialTheme);
  });

  test('user menu dropdown', async ({ page }) => {
    // Click user menu
    await page.click('[data-testid="user-menu-button"]');
    
    // Verify menu items
    await expect(page.getByText(/Профиль/i)).toBeVisible();
    await expect(page.getByText(/Настройки/i)).toBeVisible();
    await expect(page.getByText(/Выйти/i)).toBeVisible();
    
    // Click profile
    await page.click('text=Профиль');
    await expect(page).toHaveURL(/\/profile/);
  });

  test('notifications panel', async ({ page }) => {
    // Click notifications bell
    await page.click('[data-testid="notifications-button"]');
    
    // Verify panel opens
    await expect(page.locator('[data-testid="notifications-panel"]')).toBeVisible();
    
    // Check for notifications
    const notifications = page.locator('[data-testid="notification-item"]');
    const count = await notifications.count();
    
    if (count > 0) {
      // Click first notification
      await notifications.first().click();
      
      // Should mark as read
      await expect(notifications.first().locator('[data-read="true"]')).toBeVisible();
    }
  });

  test('responsive mobile navigation', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Mobile menu should be hidden
    await expect(page.locator('[data-testid="desktop-sidebar"]')).not.toBeVisible();
    
    // Open mobile menu
    await page.click('[data-testid="mobile-menu-button"]');
    
    // Verify mobile menu
    await expect(page.locator('[data-testid="mobile-sidebar"]')).toBeVisible();
    
    // Navigate
    await page.click('text=Компании');
    await expect(page).toHaveURL(/\/companies/);
    
    // Menu should close after navigation
    await expect(page.locator('[data-testid="mobile-sidebar"]')).not.toBeVisible();
  });
});

test.describe('Error Handling & Edge Cases', () => {
  test('handles 404 page not found', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    // Navigate to non-existent page
    await page.goto('/non-existent-page');
    
    // Should show 404 page
    await expect(page.getByText(/404/i)).toBeVisible();
    await expect(page.getByText(/Страница не найдена/i)).toBeVisible();
    
    // Back to dashboard link
    await page.click('text=Вернуться на главную');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('handles network error gracefully', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    // Simulate offline
    await page.context().setOffline(true);
    
    // Try to navigate
    await page.click('text=Компании');
    
    // Should show error message
    await expect(page.getByText(/Нет соединения/i)).toBeVisible();
    
    // Restore connection
    await page.context().setOffline(false);
  });

  test('session timeout redirects to login', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    // Clear auth token
    await page.evaluate(() => {
      localStorage.removeItem('vertex-ar-auth');
      localStorage.removeItem('auth_token');
    });
    
    // Try to access protected page
    await page.reload();
    
    // Should redirect to login
    await page.waitForURL('**/login', { timeout: 5000 });
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Performance & Accessibility', () => {
  test('page loads within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    const loadTime = Date.now() - startTime;
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('keyboard navigation works', async ({ page }) => {
    await page.goto('/login');
    
    // Tab through form
    await page.keyboard.press('Tab');
    await expect(page.locator('input[name="email"]')).toBeFocused();
    
    await page.keyboard.press('Tab');
    await expect(page.locator('input[name="password"]')).toBeFocused();
    
    await page.keyboard.press('Tab');
    await expect(page.locator('button:has-text("ВОЙТИ")')).toBeFocused();
  });
});
