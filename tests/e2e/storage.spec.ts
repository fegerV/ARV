import { test, expect } from '@playwright/test';

test.describe('Storage Management E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button:has-text("Login")');
    await page.waitForURL('/dashboard');
  });

  test('Storage Connections Management', async ({ page }) => {
    // Navigate to storage connections page
    await page.goto('/storage/connections');
    
    // Check if page loads
    await expect(page.locator('h1')).toContainText('Storage Connections');
    
    // Test creating local storage connection
    await page.click('button:has-text("Add Connection")');
    
    // Fill local storage form
    await page.selectOption('[data-testid="provider-select"]', 'local_disk');
    await page.fill('[data-testid="connection-name"]', 'Test Local Storage');
    await page.fill('[data-testid="base-path"]', '/tmp/test_storage');
    
    // Submit form
    await page.click('button:has-text("Create Connection")');
    
    // Check for success message or redirect
    await expect(page.locator('.success-message, .toast')).toBeVisible({ timeout: 10000 });
  });

  test('MinIO Storage Connection Setup', async ({ page }) => {
    await page.goto('/storage/connections');
    
    // Add new connection
    await page.click('button:has-text("Add Connection")');
    
    // Select MinIO provider
    await page.selectOption('[data-testid="provider-select"]', 'minio');
    await page.fill('[data-testid="connection-name"]', 'Test MinIO Storage');
    
    // Fill MinIO credentials
    await page.fill('[data-testid="minio-endpoint"]', 'minio:9000');
    await page.fill('[data-testid="minio-access-key"]', 'test-access-key');
    await page.fill('[data-testid="minio-secret-key"]', 'test-secret-key');
    await page.fill('[data-testid="minio-bucket"]', 'vertex-ar-test');
    await page.fill('[data-testid="base-path"]', '/vertex-ar');
    
    // Test connection
    await page.click('button:has-text("Test Connection")');
    
    // Wait for test result
    await expect(page.locator('.connection-status')).toBeVisible({ timeout: 15000 });
    
    // Submit form
    await page.click('button:has-text("Create Connection")');
    
    // Check for success
    await expect(page.locator('.success-message, .toast')).toBeVisible({ timeout: 10000 });
  });

  test('Yandex Disk Storage Connection Setup', async ({ page }) => {
    await page.goto('/storage/connections');
    
    // Add new connection
    await page.click('button:has-text("Add Connection")');
    
    // Select Yandex Disk provider
    await page.selectOption('[data-testid="provider-select"]', 'yandex_disk');
    await page.fill('[data-testid="connection-name"]', 'Test Yandex Disk Storage');
    
    // Fill Yandex Disk settings
    await page.fill('[data-testid="base-path"]', '/VertexAR/Test');
    
    // Simulate OAuth flow (in real test, this would open popup)
    await page.click('button:has-text("Connect Yandex Disk")');
    
    // For testing purposes, simulate successful OAuth
    await page.fill('[data-testid="oauth-token"]', 'AQAAAAATEST_TOKEN');
    await page.click('button:has-text("Verify Token")');
    
    // Submit form
    await page.click('button:has-text("Create Connection")');
    
    // Check for success
    await expect(page.locator('.success-message, .toast')).toBeVisible({ timeout: 10000 });
  });

  test('File Upload Workflow', async ({ page }) => {
    // First ensure we have a storage connection
    await page.goto('/storage/connections');
    
    // Check if connections exist, if not create one
    const connectionsCount = await page.locator('[data-testid="storage-connection-row"]').count();
    
    if (connectionsCount === 0) {
      await page.click('button:has-text("Add Connection")');
      await page.selectOption('[data-testid="provider-select"]', 'local_disk');
      await page.fill('[data-testid="connection-name"]', 'Upload Test Storage');
      await page.fill('[data-testid="base-path"]', '/tmp/upload_test');
      await page.click('button:has-text("Create Connection")');
      await page.waitForTimeout(2000);
    }
    
    // Navigate to file upload section
    await page.goto('/storage/upload');
    
    // Test file upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/test-image.jpg');
    
    // Fill upload form
    await page.fill('[data-testid="file-description"]', 'Test upload image');
    await page.selectOption('[data-testid="storage-connection"]', 'Upload Test Storage');
    
    // Upload file
    await page.click('button:has-text("Upload")');
    
    // Wait for upload completion
    await expect(page.locator('.upload-success')).toBeVisible({ timeout: 30000 });
    
    // Verify file appears in file list
    await expect(page.locator('[data-testid="file-item"]:has-text("test-image.jpg")')).toBeVisible();
  });

  test('Storage Connection Management', async ({ page }) => {
    await page.goto('/storage/connections');
    
    // Test editing existing connection
    const firstConnection = page.locator('[data-testid="storage-connection-row"]').first();
    if (await firstConnection.isVisible()) {
      await firstConnection.locator('button:has-text("Edit")').click();
      
      // Modify connection
      await page.fill('[data-testid="connection-name"]', 'Updated Storage Connection');
      await page.click('button:has-text("Save Changes")');
      
      // Verify update
      await expect(page.locator('.success-message')).toBeVisible();
    }
    
    // Test connection status
    await page.goto('/storage/connections');
    const statusButtons = page.locator('button:has-text("Test Connection")');
    const statusCount = await statusButtons.count();
    
    if (statusCount > 0) {
      await statusButtons.first().click();
      await expect(page.locator('.connection-status')).toBeVisible({ timeout: 15000 });
    }
  });

  test('Storage Settings and Configuration', async ({ page }) => {
    await page.goto('/storage/settings');
    
    // Check settings page loads
    await expect(page.locator('h1')).toContainText('Storage Settings');
    
    // Test default storage configuration
    const defaultStorageSelect = page.locator('[data-testid="default-storage-select"]');
    if (await defaultStorageSelect.isVisible()) {
      await defaultStorageSelect.selectOption({ label: 'Local Disk' });
      await page.click('button:has-text("Save Settings")');
      
      await expect(page.locator('.settings-saved')).toBeVisible();
    }
    
    // Test storage quotas
    const quotaInput = page.locator('[data-testid="storage-quota"]');
    if (await quotaInput.isVisible()) {
      await quotaInput.fill('100');
      await page.click('button:has-text("Update Quota")');
      
      await expect(page.locator('.quota-updated')).toBeVisible();
    }
  });

  test('Storage Analytics and Monitoring', async ({ page }) => {
    await page.goto('/storage/analytics');
    
    // Check analytics page loads
    await expect(page.locator('h1')).toContainText('Storage Analytics');
    
    // Test storage usage charts
    await expect(page.locator('[data-testid="storage-usage-chart"]')).toBeVisible({ timeout: 10000 });
    
    // Test file type distribution
    await expect(page.locator('[data-testid="file-type-chart"]')).toBeVisible({ timeout: 10000 });
    
    // Test upload/download statistics
    await expect(page.locator('[data-testid="transfer-stats"]')).toBeVisible();
    
    // Test date range filter
    await page.selectOption('[data-testid="date-range"]', 'last-30-days');
    await page.click('button:has-text("Apply Filter")');
    
    // Wait for data to refresh
    await page.waitForTimeout(2000);
    
    // Verify charts updated
    await expect(page.locator('[data-testid="storage-usage-chart"]')).toBeVisible();
  });
});

test.describe('Storage Error Handling', () => {
  test('Invalid Connection Configuration', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button:has-text("Login")');
    
    await page.goto('/storage/connections');
    await page.click('button:has-text("Add Connection")');
    
    // Try to create connection without required fields
    await page.selectOption('[data-testid="provider-select"]', 'minio');
    await page.click('button:has-text("Create Connection")');
    
    // Should show validation errors
    await expect(page.locator('.error-message')).toBeVisible();
  });

  test('File Upload Error Handling', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button:has-text("Login")');
    
    await page.goto('/storage/upload');
    
    // Try to upload without file
    await page.click('button:has-text("Upload")');
    
    // Should show error message
    await expect(page.locator('.error-message')).toBeVisible();
    
    // Try to upload invalid file type
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/test-executable.exe');
    
    await page.click('button:has-text("Upload")');
    
    // Should show file type error
    await expect(page.locator('.file-type-error')).toBeVisible();
  });
});