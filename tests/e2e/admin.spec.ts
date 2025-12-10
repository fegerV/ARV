import { test, expect } from '@playwright/test';

test.describe('Admin Panel E2E', () => {
  test('First-run auth flow and company creation', async ({ page }) => {
    // Test login step first
    await page.goto('/login');
    
    // Fill in credentials with the real seeded admin password
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("Login")');

    // Assert that login completes successfully
    // Should redirect to dashboard or show login success
    await expect(page).toHaveURL(/\/(dashboard|companies)?/);
    
    // Verify we're logged in by checking for admin-specific elements
    await expect(page.locator('text=Logout')).toBeVisible();
    
    // Now proceed with company creation
    await page.goto('/companies/new');
    
    // Fill company details
    await page.fill('[data-testid="company-name"]', 'Test Agency E2E');
    await page.fill('[data-testid="contact-email"]', 'test@agency.com');
    await page.fill('[data-testid="contact-phone"]', '+1234567890');
    
    // For storage, we need to handle the storage connection setup
    // This might involve OAuth flow or direct MinIO setup
    // For now, let's assume we have a test storage connection
    
    // Simulate storage connection selection
    await page.selectOption('[data-testid="storage-connection"]', 'test-storage');
    
    // Set subscription details
    await page.selectOption('[data-testid="subscription-tier"]', 'basic');
    await page.fill('[data-testid="storage-quota"]', '10');
    await page.fill('[data-testid="projects-limit"]', '5');

    // Submit the form
    await page.click('button:has-text("Create Company")');
    
    // Assert company creation succeeds
    await expect(page).toHaveURL(/\/companies\/\d+/);
    await expect(page.locator('text=Test Agency E2E')).toBeVisible();
    
    // Test protected access - try to access a protected endpoint
    await page.goto('/api/auth/me');
    // This should return JSON user data, not an error
    const response = await page.evaluate(async () => {
      const response = await fetch('/api/auth/me');
      return {
        status: response.status,
        data: await response.json()
      };
    });
    
    expect(response.status).toBe(200);
    expect(response.data.email).toBe('admin@vertexar.com');
    expect(response.data.role).toBe('admin');
  });

  test('Unauthorized access rejection', async ({ page }) => {
    // Test that protected routes reject unauthenticated access
    await page.goto('/companies/new');
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    
    // Try to access API endpoint directly
    const response = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/companies/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: 'Unauthorized Company',
            contact_email: 'test@example.com',
            storage_connection_id: 1
          })
        });
        return {
          status: response.status,
          data: await response.json()
        };
      } catch (error) {
        return { error: error.message };
      }
    });
    
    expect(response.status).toBe(401);
    expect(response.data.detail).toContain('Could not validate credentials');
  });

  test('Valid token allows protected operations', async ({ page }) => {
    // First login to get a token
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@vertexar.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button:has-text("Login")');
    
    // Wait for login to complete
    await page.waitForURL(/\/(dashboard|companies)?/);
    
    // Get the auth token from localStorage or cookies
    const token = await page.evaluate(() => {
      return localStorage.getItem('auth_token') || 
             document.cookie.split(';')
               .find(cookie => cookie.trim().startsWith('auth_token='))
               ?.split('=')[1];
    });
    
    expect(token).toBeTruthy();
    
    // Use the token to access protected API
    const response = await page.evaluate(async (authToken) => {
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      return {
        status: response.status,
        data: await response.json()
      };
    }, token);
    
    expect(response.status).toBe(200);
    expect(response.data.email).toBe('admin@vertexar.com');
  });
});
