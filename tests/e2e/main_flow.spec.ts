import { test, expect } from '@playwright/test';

test.describe('Main Application Flow E2E Tests', () => {
  
  test('can login and view dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/(dashboard|companies)/);
  });

  test('login/logout flow', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Verify login success
    await expect(page.locator('text=Logout')).toBeVisible();
    await expect(page.locator('text=Dashboard')).toBeVisible();
    
    // Logout
    await page.click('text=Logout');
    
    // Verify logout success
    await expect(page).toHaveURL('/login');
    await expect(page.locator('text=Login')).toBeVisible();
  });

  test('dashboard loading', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Navigate to dashboard
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/\/(dashboard|companies)/);
    await expect(page.locator('text=Dashboard')).toBeVisible();
    await expect(page.locator('text=Total Companies')).toBeVisible();
    await expect(page.locator('text=Total Projects')).toBeVisible();
    await expect(page.locator('text=Total AR Content')).toBeVisible();
  });

  test('CRUD operations for companies', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Create company
    await page.click('text=Companies');
    await page.click('text=New Company');
    await page.fill('[data-testid="company-name"]', 'Test Company E2E');
    await page.fill('[data-testid="contact-email"]', 'test@company.com');
    await page.fill('[data-testid="contact-phone"]', '+1234567890');
    await page.click('button:has-text("Create Company")');
    
    // Verify company creation
    await expect(page.locator('text=Test Company E2E')).toBeVisible();
    
    // Edit company
    await page.click('text=Edit');
    await page.fill('[data-testid="company-name"]', 'Updated Test Company E2E');
    await page.click('button:has-text("Save Changes")');
    
    // Verify update
    await expect(page.locator('text=Updated Test Company E2E')).toBeVisible();
    
    // Delete company
    await page.click('text=Delete');
    await page.click('button:has-text("Confirm")');
    
    // Verify deletion
    await expect(page.locator('text=Updated Test Company E2E')).not.toBeVisible();
  });

  test('CRUD operations for projects', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Create project
    await page.click('text=Projects');
    await page.click('text=New Project');
    await page.fill('[data-testid="project-name"]', 'Test Project E2E');
    await page.fill('[data-testid="project-description"]', 'Test project description');
    await page.click('button:has-text("Create Project")');
    
    // Verify project creation
    await expect(page.locator('text=Test Project E2E')).toBeVisible();
    
    // Edit project
    await page.click('text=Edit');
    await page.fill('[data-testid="project-name"]', 'Updated Test Project E2E');
    await page.click('button:has-text("Save Changes")');
    
    // Verify update
    await expect(page.locator('text=Updated Test Project E2E')).toBeVisible();
    
    // Delete project
    await page.click('text=Delete');
    await page.click('button:has-text("Confirm")');
    
    // Verify deletion
    await expect(page.locator('text=Updated Test Project E2E')).not.toBeVisible();
  });

  test('CRUD operations for AR content', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Create AR content
    await page.click('text=AR Content');
    await page.click('text=New AR Content');
    await page.fill('[data-testid="ar-content-title"]', 'Test AR Content E2E');
    await page.fill('[data-testid="ar-content-description"]', 'Test AR content description');
    
    // Upload image marker
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('../valid_test_image.png');
    
    await page.click('button:has-text("Create AR Content")');
    
    // Verify AR content creation
    await expect(page.locator('text=Test AR Content E2E')).toBeVisible();
    
    // Edit AR content
    await page.click('text=Edit');
    await page.fill('[data-testid="ar-content-title"]', 'Updated Test AR Content E2E');
    await page.click('button:has-text("Save Changes")');
    
    // Verify update
    await expect(page.locator('text=Updated Test AR Content E2E')).toBeVisible();
    
    // Delete AR content
    await page.click('text=Delete');
    await page.click('button:has-text("Confirm")');
    
    // Verify deletion
    await expect(page.locator('text=Updated Test AR Content E2E')).not.toBeVisible();
  });

  test('navigation and routing', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@vertexar.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Test navigation to all main pages
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/\/(dashboard|companies)/);
    
    await page.click('text=Companies');
    await expect(page).toHaveURL(/\/companies/);
    
    await page.click('text=Projects');
    await expect(page).toHaveURL(/\/projects/);
    
    await page.click('text=AR Content');
    await expect(page).toHaveURL(/\/ar-content/);
    
    await page.click('text=Settings');
    await expect(page).toHaveURL(/\/settings/);
    
    await page.click('text=Analytics');
    await expect(page).toHaveURL(/\/analytics/);
  });
});