import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.context().clearCookies();
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    await expect(page).toHaveTitle(/Vertex AR Admin/);
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /войти/i })).toBeVisible();
  });

  test('successful login redirects to dashboard', async ({ page }) => {
    // Fill in login form
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    
    // Submit form
    await page.click('button:has-text("ВОЙТИ")');
    
    // Wait for navigation
    await page.waitForURL('**/dashboard');
    
    // Verify dashboard loaded
    await expect(page.getByText(/dashboard/i)).toBeVisible();
    await expect(page.locator('[data-testid="kpi-card"]')).toBeVisible();
  });

  test('failed login shows error message', async ({ page }) => {
    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button:has-text("ВОЙТИ")');
    
    // Should show error message
    await expect(page.getByText(/неверный email или пароль/i)).toBeVisible();
    
    // Should remain on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('empty form shows validation errors', async ({ page }) => {
    await page.click('button:has-text("ВОЙТИ")');
    
    // Should show validation messages
    await expect(page.getByText(/email обязателен/i)).toBeVisible();
    await expect(page.getByText(/пароль обязателен/i)).toBeVisible();
  });

  test('password visibility toggle works', async ({ page }) => {
    const passwordInput = page.locator('input[name="password"]');
    
    // Initially password type
    await expect(passwordInput).toHaveAttribute('type', 'password');
    
    // Click visibility toggle
    await page.click('[data-testid="toggle-password"]');
    
    // Should be text type
    await expect(passwordInput).toHaveAttribute('type', 'text');
    
    // Click again to hide
    await page.click('[data-testid="toggle-password"]');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('logout clears session and redirects to login', async ({ page }) => {
    // Login first
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    // Click user menu
    await page.click('[data-testid="user-menu-button"]');
    
    // Click logout
    await page.click('text=Выйти');
    
    // Should redirect to login
    await page.waitForURL('**/login');
    await expect(page).toHaveURL(/\/login/);
  });
});
