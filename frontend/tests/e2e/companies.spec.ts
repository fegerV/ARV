import { test, expect } from '@playwright/test';

test.describe('Company CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
  });

  test('should navigate to companies list', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    await expect(page.getByRole('heading', { name: /компании/i })).toBeVisible();
    await expect(page.locator('[data-testid="companies-table"]')).toBeVisible();
  });

  test('should create new company', async ({ page }) => {
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click create button
    await page.click('text=Новая компания');
    await page.waitForURL('**/companies/new');
    
    // Fill form
    await page.fill('[data-testid="company-name"]', 'Test Agency E2E');
    await page.check('input[value="local_disk"]');
    
    // Submit
    await page.click('[data-testid="create-company-button"]');
    
    // Wait for redirect
    await page.waitForURL(/\/companies\/\d+/);
    
    // Verify company created
    await expect(page.getByText('Test Agency E2E')).toBeVisible();
    await expect(page.getByText(/компания создана/i)).toBeVisible();
  });

  test('should view company details', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click on first company
    await page.click('[data-testid="company-row"]:first-child');
    
    // Verify details page
    await expect(page.locator('[data-testid="company-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="company-storage-info"]')).toBeVisible();
    await expect(page.locator('[data-testid="company-projects-list"]')).toBeVisible();
  });

  test('should edit company', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click edit button
    await page.click('[data-testid="edit-company-button"]:first-child');
    
    // Update name
    const nameInput = page.locator('[data-testid="company-name"]');
    await nameInput.clear();
    await nameInput.fill('Updated Company Name');
    
    // Save
    await page.click('[data-testid="save-company-button"]');
    
    // Verify update
    await expect(page.getByText(/изменения сохранены/i)).toBeVisible();
    await expect(page.getByText('Updated Company Name')).toBeVisible();
  });

  test('should delete company with confirmation', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click delete button
    await page.click('[data-testid="delete-company-button"]:first-child');
    
    // Confirm deletion in dialog
    await expect(page.getByText(/вы уверены/i)).toBeVisible();
    await page.click('button:has-text("Удалить")');
    
    // Verify deletion
    await expect(page.getByText(/компания удалена/i)).toBeVisible();
  });

  test('should filter companies list', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Use search filter
    await page.fill('[data-testid="search-companies"]', 'Test Agency');
    
    // Wait for filter results
    await page.waitForTimeout(500);
    
    // Verify filtered results
    const rows = page.locator('[data-testid="company-row"]');
    const count = await rows.count();
    
    expect(count).toBeGreaterThan(0);
    await expect(rows.first()).toContainText('Test Agency');
  });

  test('should sort companies table', async ({ page }) => {
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
    
    // Click name column header to sort
    await page.click('[data-testid="sort-by-name"]');
    
    // Wait for sort animation
    await page.waitForTimeout(300);
    
    // Verify sorting indicator
    await expect(page.locator('[data-testid="sort-by-name"][data-sorted="asc"]')).toBeVisible();
  });
});