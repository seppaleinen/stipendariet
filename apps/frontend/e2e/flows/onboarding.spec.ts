import { test } from '@playwright/test';
import { AuthPage } from '../pages/auth.page';
import { ProfilePage }    from '../pages/profile.page';
import { FamilyPage }     from '../pages/family.page';

test.describe('Onboarding Flow', () => {
  test('complete profile and family setup', async ({ page }) => {
    const authPage = new AuthPage(page);
    const profilePage = new ProfilePage(page);
    const familyPage = new FamilyPage(page);

    // 1. Registration
    await authPage.goto();
    await authPage.switchToSignup();
    await authPage.signup('Test User', 'test@example.com', 'password123');
    
    // Wait for redirection to profile setup (assuming auth redirect)
    await profilePage.goto();

    // 2. Profile Setup
    await profilePage.fillBasicInfo('Test User');
    await profilePage.selectGeography('Uppsala', 'Uppsala');
    await profilePage.selectLifeSituations(['Student']);
    await profilePage.selectHealthConditions(['Allergy']);
    await profilePage.selectOccupations(['Journalism']);
    await profilePage.selectSupportPurposes(['Education']);
    await profilePage.save();

    // 3. Family Setup
    await familyPage.goto();
    await familyPage.fillNeeds('I am looking for help with my studies.');
    await familyPage.save();
  });
});
