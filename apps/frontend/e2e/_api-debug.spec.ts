import { test, expect } from '@playwright/test';

test('debug: check what API the browser sees', async ({ page }) => {
  // Clear any existing auth session so we land on /auth instead of being redirected.
  // Use addInitScript to clear localStorage before any page script runs (avoids
  // SecurityError in sandboxed iframes/cross-origin contexts).
  await page.context().addInitScript(() => {
    localStorage.removeItem('auth_access_token');
    localStorage.removeItem('auth_refresh_token');
  });
  await page.context().clearCookies();

  const responses: string[] = [];
  page.on('response', r => {
    if (r.url().includes('/api')) responses.push(`${r.status()} ${r.url()}`);
  });

  await page.goto('http://localhost:8080/auth');
  await page.waitForSelector('#login-email', { timeout: 10000 });
  console.log('API responses:', responses);

  // Fill and submit login
  await page.fill('#login-email', 'admin@stipendie.labb.site');
  await page.fill('#login-password', 'changeme');
  await page.getByRole("button", { name: /^Logga in$/ }).click();

  // Wait a bit and collect more responses
  await page.waitForTimeout(2000);
  const afterLogin = responses.filter(r => r.includes('/api'));
  console.log('After login responses:', afterLogin);
  console.log('Current URL:', page.url());
});
