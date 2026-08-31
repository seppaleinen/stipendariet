import { Page, Locator } from '@playwright/test';

export class FamilyPage {
  readonly page: Page;
  // /family-setup routes to the same ProfileSetup component which has a
  // self-description textarea with this placeholder.
  readonly needsTextarea: Locator;
  readonly saveButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.needsTextarea = page.getByPlaceholder(/Beskriv din situation, dina behov och vad du söker stöd för/i);
    this.saveButton = page.getByRole('button', { name: 'Spara profil' });
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
