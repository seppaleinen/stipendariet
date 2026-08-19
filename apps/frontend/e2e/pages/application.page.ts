import { Page, Locator } from '@playwright/test';

export class ApplicationPage {
  readonly page: Page;
  readonly newApplicationButton: Locator;
  readonly applicationTabs: (status: 'all' | 'draft' | 'submitted' | 'approved' | 'rejected') => Locator;
  readonly applicationCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.newApplicationButton = page.getByRole('link', { name: 'Ny Ansökan' });
    this.applicationTabs = (status) => {
      const names = {
        all: 'Alla',
        draft: 'Utkast',
        submitted: 'Inskickad',
        approved: 'Godkänd',
        rejected: 'Avslagen'
      };
      return page.getByRole('tab', { name: names[status] });
    };
    this.applicationCards = page.locator('div.card'); // Assuming similar structure
  }

  async goto() {
    await this.page.goto('/applications');
  }

  async startNewApplication() {
    await this.newApplicationButton.click();
  }

  async filterByStatus(status: 'all' | 'draft' | 'submitted' | 'approved' | 'rejected') {
    await this.applicationTabs(status).click();
  }

  async getApplicationCard(title: string) {
    return this.page.locator('div.card').filter({ hasText: title });
  }
}
