import { Page, Locator } from '@playwright/test';

export class GrantPage {
  readonly page: Page;
  readonly searchInput: Locator;
  readonly categorySelect: Locator;
  readonly grantCards: Locator;
  readonly nextPageButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.searchInput = page.getByRole('textbox', { name: /Sök stipendier/i });
    this.categorySelect = page.getByRole('combobox');
    this.grantCards = page.locator('div.bg-card');
  }

  async goto() {
    await this.page.goto('/grants');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    // Wait for debounce if necessary.
  }

  async selectCategory(category: string) {
    await this.categorySelect.selectOption({ label: category });
  }

  async getGrantCard(title: string) {
    return this.page.locator('div.bg-card').filter({ hasText: title });
  }

  async bookmarkGrant(title: string) {
    const card = this.getGrantCard(title);
    await card.getByRole('button', { name: /Spara|Ta bort/i }).click();
  }

  async clickGrant(title: string) {
    await this.getGrantCard(title).getByRole('link', { name: /Läs mer/i }).click();
  }
}
