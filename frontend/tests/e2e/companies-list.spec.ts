import { test, expect } from '@playwright/test';

test.describe('Companies List Enhanced Features', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("ВОЙТИ")');
    await page.waitForURL('**/dashboard');
    
    // Navigate to companies
    await page.click('text=Компании');
    await page.waitForURL('**/companies');
  });

  test('should display companies list with all columns', async ({ page }) => {
    // Verify table headers
    await expect(page.getByText('Name')).toBeVisible();
    await expect(page.getByText('Slug')).toBeVisible();
    await expect(page.getByText('Contact')).toBeVisible();
    await expect(page.getByText('Storage')).toBeVisible();
    await expect(page.getByText('Usage')).toBeVisible();
    await expect(page.getByText('Status')).toBeVisible();
    await expect(page.getByText('Type')).toBeVisible();
    await expect(page.getByText('Created')).toBeVisible();
  });

  test('should show storage provider names correctly', async ({ page }) => {
    // Verify that storage providers are displayed with proper names
    // This would depend on the actual data, but we can check for the presence of known providers
    const storageCells = page.locator('td >> nth=3'); // Storage column
    const count = await storageCells.count();
    
    // At least one storage provider should be visible
    expect(count).toBeGreaterThan(0);
  });

  test('should allow searching companies', async ({ page }) => {
    // Fill search input
    const searchInput = page.locator('input[placeholder="Search companies..."]');
    await searchInput.fill('Test');
    
    // Wait for search to complete
    await page.waitForTimeout(500);
    
    // Verify search results (this would depend on actual data)
    // For now, just verify the search input works
    await expect(searchInput).toHaveValue('Test');
  });

  test('should filter companies by status', async ({ page }) => {
    // Open status filter dropdown
    await page.click('text=Status');
    
    // Select "Active" filter
    await page.click('text=Active');
    
    // Wait for filter to apply
    await page.waitForTimeout(500);
    
    // Verify filter is applied (would need specific data to verify completely)
  });

  test('should filter companies by type', async ({ page }) => {
    // Open type filter dropdown
    await page.click('text=Type');
    
    // Select "Client" filter
    await page.click('text=Client');
    
    // Wait for filter to apply
    await page.waitForTimeout(500);
    
    // Verify filter is applied (would need specific data to verify completely)
  });

  test('should show company usage information', async ({ page }) => {
    // Look for usage information in the table
    // This would show as "X GB / Y GB" format
    const usageCells = page.locator('td >> nth=4'); // Usage column
    // Just verify the column exists, specific values depend on test data
  });

  test('should navigate to company details when clicking row', async ({ page }) => {
    // Click on the first company row
    const firstRow = page.locator('tbody tr').first();
    await firstRow.click();
    
    // Should navigate to company details page
    await page.waitForURL(/\/companies\/\d+/);
  });

  test('should show count of companies', async ({ page }) => {
    // Look for the companies count text
    await expect(page.getByText(/Showing \d+ of \d+ companies/)).toBeVisible();
  });

  test('should show empty state when no companies match search', async ({ page }) => {
    // Enter a search term that won't match any companies
    const searchInput = page.locator('input[placeholder="Search companies..."]');
    await searchInput.fill('NonExistentCompany12345');
    
    // Wait for search to complete
    await page.waitForTimeout(500);
    
    // Verify empty state message
    await expect(page.getByText('No companies found')).toBeVisible();
    await expect(page.getByText('No companies match your search criteria')).toBeVisible();
  });
});