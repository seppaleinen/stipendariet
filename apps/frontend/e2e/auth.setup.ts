import { test as base } from '@playwright/test';
import { AuthPage } from './pages/auth.page';

export const STORAGE_STATE = './e2e/auth.json';

base.beforeEach(async ({ page }) => {
  await page.goto('/');
});

base.test.describe('Authentication Setup', () => {
  base.test('login via email', async ({ page }) => {
    const authPage = new AuthPage(page);
    await authPage.goto();
    
    // For testing, we'll use dummy credentials. 
    // In a real CI environment, these would be environment variables.
    const email = 'test@example.com';
    const password = 'password123';

    await authPage.login(email, password);
    
    // Verify login success by checking for a specific element or redirect
    await base.expect(page.getByText(/Välkommen tillbaka/i)).toBeVisible({ timeout: 10000 });
    
    // Save storage state
    await page.context().storageState({ path: STORAGE_STATE });
  });
});
