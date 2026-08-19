import { Page, Locator } from '@playwright/test';

export class FamilyPage {
  readonly page: Page;
  readonly needsTextarea: Locator;
  readonly saveButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.needsTextarea = page.getByPlaceholder(/Beskriv din situation och varför du söker bidrag eller stipendium\.\.\./i);
    this.saveButton = page.getByRole('button', { name: 'Spara' });
  }

  async goto() {
    await this.page.goto('/family-setup');
  }

  async fillNeeds(text: string) {
    await this.needsTextarea.fill(text);
  }

  async save() {
    await this.saveButton.click();
  }
}
