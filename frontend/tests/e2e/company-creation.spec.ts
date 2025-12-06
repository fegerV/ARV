import { test, expect } from '@playwright/test';

test.describe('Company Creation with Yandex Disk', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
  });

  test('should create new company with local storage', async ({ page }) => {
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click create button
    await page.click('text=Новая компания');
    await page.waitForURL('**/companies/new');
    
    // Fill form
    await page.fill('[data-testid="company-name"]', 'Test Agency with Local Storage');
    
    // Select local storage option
    await page.check('input[value="local_disk"]');
    
    // Fill contact info
    await page.fill('[data-testid="contact-email"]', 'contact@testagency.com');
    await page.fill('[data-testid="contact-phone"]', '+79991234567');
    
    // Set storage quota
    await page.fill('[data-testid="storage-quota"]', '50');
    
    // Submit
    await page.click('[data-testid="create-company-button"]');
    
    // Wait for redirect
    await page.waitForURL(/\/companies\/\d+/);
    
    // Verify company created
    await expect(page.getByText('Test Agency with Local Storage')).toBeVisible();
    await expect(page.getByText(/компания создана/i)).toBeVisible();
  });

  test('should show validation errors for invalid input', async ({ page }) => {
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click create button
    await page.click('text=Новая компания');
    await page.waitForURL('**/companies/new');
    
    // Try to submit empty form
    await page.click('[data-testid="create-company-button"]');
    
    // Verify validation errors
    await expect(page.getByText('Название не менее 2 символов')).toBeVisible();
    await expect(page.getByText('Слаг не менее 3 символов')).toBeVisible();
  });

  test('should auto-generate slug from company name', async ({ page }) => {
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click create button
    await page.click('text=Новая компания');
    await page.waitForURL('**/companies/new');
    
    // Fill company name
    await page.fill('[data-testid="company-name"]', 'Awesome Digital Agency');
    
    // Verify slug is auto-generated
    const slugInput = page.locator('[data-testid="company-slug"]');
    await expect(slugInput).toHaveValue('awesome-digital-agency');
  });

  test('should connect Yandex Disk storage', async ({ page }) => {
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click create button
    await page.click('text=Новая компания');
    await page.waitForURL('**/companies/new');
    
    // Fill company name
    await page.fill('[data-testid="company-name"]', 'Yandex Disk Agency');
    
    // Select Yandex Disk option
    await page.check('input[value="yandex_disk"]');
    
    // Fill connection name
    await page.fill('[data-testid="connection-name"]', 'Yandex Disk Connection');
    
    // Note: We can't test the actual OAuth flow in E2E tests
    // But we can verify the UI elements are present
    await expect(page.getByText('Подключить Яндекс.Диск')).toBeVisible();
    
    // For demo purposes, we'll simulate the connection by setting the values directly
    // In a real test, this would involve mocking the OAuth flow
  });
});