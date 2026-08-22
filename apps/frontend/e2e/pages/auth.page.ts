import { Page, Locator } from '@playwright/test';

export class AuthPage {
  readonly page: Page;
  readonly loginTab: Locator;
  readonly signupTab: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly googleLoginButton: Locator;
  readonly nameInput: Locator;
  readonly signupEmailInput: Locator;
  readonly signupPasswordInput: Locator;
  readonly signupConfirmPasswordInput: Locator;
  readonly signupButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.loginTab = page.getByRole('tab', { name: 'Logga in' });
    this.signupTab = page.getByRole('tab', { name: 'Skapa konto' });
    
    // Login Form
    this.emailInput = page.getByLabel('E-post');
    this.passwordInput = page.getByLabel('Lösenord');
    this.loginButton = page.getByRole('button', { name: 'Logga in' });
    this.googleLoginButton = page.getByRole('button', { name: 'Fortsätt med Google' });

    // Signup Form
    this.nameInput = page.getByLabel('Namn (valfritt)');
    this.signupEmailInput = page.getByLabel('E-post');
    this.signupPasswordInput = page.getByLabel('Lösenord');
    this.signupConfirmPasswordInput = page.getByLabel('Bekräfta lösenord');
    this.signupButton = page.getByRole('button', { name: 'Skapa konto' });
  }

  async goto() {
    await this.page.goto('/auth');
  }

  async switchToLogin() {
    await this.loginTab.click();
  }

  async switchToSignup() {
    await this.signupTab.click();
  }

  async login(email: string, pass: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(pass);
    await this.loginButton.click();
  }

  async signup(name: string, email: string, pass: string) {
    await this.nameInput.fill(name);
    await this.signupEmailInput.fill(email);
    await this.signupPasswordInput.fill(pass);
    await this.signupConfirmPasswordInput.fill(pass);
    await this.signupButton.click();
  }
}
