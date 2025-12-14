import { test, expect } from '@playwright/test';

test.describe('Security Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.goto('/');
    await page.evaluate(() => {
      sessionStorage.clear();
      localStorage.clear();
    });
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Try to access protected route directly
    await page.goto('/dashboard');
    
    // Should be redirected to login
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should store tokens in sessionStorage, not localStorage', async ({ page }) => {
    // Navigate to signup and create account
    await page.goto('/signup');
    
    const uniqueEmail = `security_test_${Date.now()}@example.com`;
    await page.getByLabel('E-mail').fill(uniqueEmail);
    await page.getByLabel('Senha', { exact: true }).fill('SecurePassword123!');
    await page.getByLabel('Confirmar Senha').fill('SecurePassword123!');
    await page.getByRole('button', { name: 'Cadastrar' }).click();
    
    // Wait for redirect to login
    await expect(page).toHaveURL(/.*\/login/);
    
    // Login
    await page.getByLabel('E-mail').fill(uniqueEmail);
    await page.getByLabel('Senha', { exact: true }).fill('SecurePassword123!');
    await page.getByRole('button', { name: 'Entrar' }).click();
    
    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // Verify token is in sessionStorage
    const sessionToken = await page.evaluate(() => sessionStorage.getItem('access_token'));
    expect(sessionToken).not.toBeNull();
    
    // Verify token is NOT in localStorage (security check)
    const localToken = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(localToken).toBeNull();
  });

  test('should clear tokens on logout', async ({ page }) => {
    // First, set a mock token
    await page.goto('/login');
    await page.evaluate(() => {
      sessionStorage.setItem('access_token', 'test-token');
    });
    
    // Navigate to dashboard (with mock token, may or may not work depending on backend validation)
    await page.goto('/dashboard');
    
    // If we're on login, that's expected (backend rejected mock token)
    // If we're on dashboard, find and click logout
    const currentUrl = page.url();
    
    if (currentUrl.includes('/dashboard')) {
      // Look for logout button/menu
      const logoutButton = page.getByRole('button', { name: /logout|sair|desconectar/i });
      if (await logoutButton.isVisible()) {
        await logoutButton.click();
      }
    }
    
    // After logout (or being kicked out), verify tokens are cleared
    const token = await page.evaluate(() => sessionStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

  test('should handle expired/invalid token gracefully', async ({ page }) => {
    // Set an invalid token
    await page.goto('/login');
    await page.evaluate(() => {
      sessionStorage.setItem('access_token', 'invalid-expired-token-12345');
    });
    
    // Try to access protected route
    await page.goto('/dashboard');
    
    // Should redirect to login (backend returns 401, client clears token)
    await expect(page).toHaveURL(/.*\/login/, { timeout: 10000 });
    
    // Token should be cleared after 401
    const token = await page.evaluate(() => sessionStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

  test('should not expose sensitive data in page source', async ({ page }) => {
    await page.goto('/login');
    
    const pageContent = await page.content();
    
    // Check that no tokens or sensitive patterns are in the HTML source
    expect(pageContent).not.toContain('access_token');
    expect(pageContent).not.toContain('refresh_token');
    expect(pageContent).not.toContain('Bearer ');
  });
});
