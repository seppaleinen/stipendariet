import { Page, Locator } from '@playwright/test';

export class ProfilePage {
  readonly page: Page;
  readonly nameInput: Locator;
  readonly countySelect: Locator;
  readonly municipalitySelect: Locator;
  readonly lifeSituations: (label: string) => Locator;
  readonly healthConditions: (label: string) => Locator;
  readonly occupations: (label: string) => Locator;
  readonly supportPurposes: (label: string) => Locator;
  readonly saveButton: Locator;
  readonly nextButton: Locator;
  readonly previousButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.nameInput = page.getByLabel('Namn på profil (t.ex. Klient A)');
    this.countySelect = page.getByLabel('Län');
    this.municipalitySelect = page.getByLabel('Kommun');
    
    this.lifeSituations = (label: string) => page.getByRole('checkbox', { name: label });
    this.healthConditions = (label: string) => page.getByRole('checkbox', { name: label });
    this.occupations = (label: string) => page.getByRole('checkbox', { name: label });
    this.supportPurposes = (label: string) => page.getByRole('checkbox', { name: label });
    
    this.saveButton = page.getByRole('button', { name: 'Spara profil' });
    this.nextButton = page.getByRole('button', { name: 'Nästa' });
    this.previousButton = page.getByRole('button', { name: 'Föregående' });
  }

  async goto() {
    await this.page.goto('/profile-setup');
  }

  async fillBasicInfo(name: string) {
    await this.nameInput.fill(name);
  }

  async selectGeography(county: string, municipality: string) {
    await this.countySelect.selectOption({ label: county });
    await this.municipalitySelect.selectOption({ label: municipality });
  }

  async selectLifeSituations(items: string[]) {
    for (const item of items) {
      await this.lifeSituations(item).check();
    }
  }

  async selectHealthConditions(items: string[]) {
    for (const item of items) {
      await this.healthConditions(item).check();
    }
  }

  async selectOccupations(items: string[]) {
    for (const item of items) {
      await this.occupations(item).check();
    }
  }

  async selectSupportPurposes(items: string[]) {
    for (const item of items) {
      await this.supportPurposes(item).check();
    }
  }

  async save() {
    await this.saveButton.click();
  }

  async next() {
    await this.nextButton.click();
  }

  async previous() {
    await this.previousButton.click();
  }
}
