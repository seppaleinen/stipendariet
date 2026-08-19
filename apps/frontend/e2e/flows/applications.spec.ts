import { test, expect } from '@playwright/test';
import { GrantPage } from '../pages/grant.page';
import { ApplicationPage } from '../pages/application.page';

test.describe('Application Lifecycle', () => {
  test('create and track application', async ({ page }) => {
    const grantPage = new GrantPage(page);
    const appPage = new ApplicationPage(page);

    // 1. Discover Grants
    await grantPage.goto();
    await grantPage.search('stipendium');
    
    // 2. View Grant Details
    // Note: This assumes there is a grant with a certain title or we find it from the list.
    // For simplicity in E2E, we'll wait for cards and pick the first one.
    await page.waitForSelector('div.card');
    const firstGrantTitle = await page.locator('div.card h3').first().innerText();
    await grantPage.clickGrant(firstGrantTitle);

    // 3. Start Application
    await appPage.goto(); // or use the 'Start Application' button from GrantDetail
    // Actually, let's use the button in GrantDetail
    await page.getByRole('link', { name: /Starta Ansökan/i }).click();

    // 4. Check status in Applications list
    await appPage.goto();
    await expect(appPage.applicationTabs('draft')).toBeVisible();
  });
});
