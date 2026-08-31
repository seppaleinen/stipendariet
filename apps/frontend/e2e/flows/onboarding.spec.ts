import { test, expect } from '@playwright/test';
import { AuthPage } from '../pages/auth.page';
import { ProfilePage }    from '../pages/profile.page';
import { FamilyPage }     from '../pages/family.page';

test.describe('Onboarding Flow', () => {
  test('complete profile and family setup', async ({ page }) => {
    const authPage = new AuthPage(page);
    const profilePage = new ProfilePage(page);
    const familyPage = new FamilyPage(page);

    // 1. Registration — use a unique email to avoid 409 conflict on re-runs.
    // Clear session state to start fresh.
    await page.context().clearCookies();
    await page.request.fetch('http://localhost:8000/api/auth/logout', { ignoreHTTPSErrors: true });
    await page.goto('/auth');
    await page.evaluate(() => {
      localStorage.removeItem('auth_access_token');
      localStorage.removeItem('auth_refresh_token');
    });
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should now show the auth form.
    await authPage.switchToSignup();
    await expect(authPage.signupTab).toBeVisible();
    await expect(authPage.nameInput).toBeVisible({ timeout: 10000 });
    const email = `test+${Date.now()}@example.com`;
    await authPage.signup('Test User', email, 'password123');

    // Wait for redirect away from /auth.
    await expect(page).not.toHaveURL(/\/auth/, { timeout: 15000 });

    // 2. Profile Setup — use the API to create a profile and set it as active,
    // then navigate to /profile-setup where the form renders.
    const { access_token } = await page.evaluate(() => ({
      access_token: localStorage.getItem('auth_access_token'),
    }));
    const created = await page.request.fetch('http://localhost:8000/api/profile/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${access_token}`,
      },
      data: { name: 'Test User' },
      ignoreHTTPSErrors: true,
    });
    const profile = await created.json();
    // Persist activeProfileId so ProfileContext loads with an active profile.
    await page.evaluate((id: number) => {
      localStorage.setItem('activeProfileId', String(id));
    }, profile.id);

    await profilePage.goto();
    await expect(page.getByLabel('Namn på profil (t.ex. Klient A)')).toBeVisible({ timeout: 10000 });
    await profilePage.fillBasicInfo('Test User');
    await profilePage.selectGeography('Uppsala län', 'Uppsala');
    await profilePage.selectLifeSituations(['Student']);
    await profilePage.selectHealthConditions(['Allergi']);
    await profilePage.selectOccupations(['Journalistik']);
    await profilePage.selectSupportPurposes(['Utbildning']);
    await profilePage.save();

    // 3. Family Setup
    await familyPage.goto();
    await familyPage.fillNeeds('I am looking for help with my studies.');
    await familyPage.save();
  });
});
