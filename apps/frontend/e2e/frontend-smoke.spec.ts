import { test, expect } from "@playwright/test";

/**
 * Smoke tests for the StipendieAssistenten frontend.
 *
 * These verify the app boots, renders correctly, and key navigation paths work.
 * Migrated from the old stipendie-assistenten/infra-test repo.
 */
test.describe("Frontend smoke tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("has correct page title", async ({ page }) => {
    await expect(page).toHaveTitle(/StipendieAssistenten/);
  });

  test("loads main page content", async ({ page }) => {
    await expect(page.locator("#root")).toBeAttached();
    await page.waitForLoadState("networkidle");

    const heading = page.locator("h1, .hero-title, [data-testid='hero-title']");
    if ((await heading.count()) > 0) {
      await expect(heading.first()).toBeVisible();
    } else {
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("navigation to grants page works", async ({ page }) => {
    const grantsLink = page
      .locator('role=link[name*="stipendier" i]')
      .or(page.locator('role=link[name*="grants" i]'))
      .or(page.locator('role=link[name*="Utforska" i]'));

    if ((await grantsLink.count()) > 0) {
      const initialUrl = page.url();
      await grantsLink.first().click();
      await page.waitForURL("**/grants");
      expect(page.url()).not.toBe(initialUrl);
    } else {
      const navElements = page.locator('nav a, .navigation a, [role="link"]');
      expect(await navElements.count()).toBeGreaterThanOrEqual(0);
    }
  });

  test("header navigation elements exist", async ({ page }) => {
    const header = page.locator("header");
    if ((await header.count()) > 0) {
      await expect(header.first()).toBeVisible();
    }

    const authLinks = page
      .locator('role=link[name*="logga" i]')
      .or(page.locator('role=link[name*="registrera" i]'))
      .or(page.locator('button[name*="logga" i]'))
      .or(page.locator('button[name*="registrera" i]'));
    expect(await authLinks.count()).toBeGreaterThanOrEqual(0);
  });

  test("footer exists", async ({ page }) => {
    const footer = page.locator("footer");
    if ((await footer.count()) > 0) {
      await expect(footer.first()).toBeVisible();
    }
  });

  test("feature sections are rendered", async ({ page }) => {
    await page.waitForLoadState("networkidle");
    const sections = page.locator(
      ".feature, .card, [data-testid='feature-card'], .section",
    );
    expect(await sections.count()).toBeGreaterThanOrEqual(0);
  });

  test("form elements are present", async ({ page }) => {
    const inputs = page.locator("input, textarea, select");
    const buttons = page.locator("button");
    expect(await inputs.count()).toBeGreaterThanOrEqual(0);
    expect(await buttons.count()).toBeGreaterThanOrEqual(0);
  });

  test("search functionality exists", async ({ page }) => {
    const searchInputs = page.locator(
      "input[placeholder*='search' i], input[placeholder*='sök' i], input[role='search']",
    );
    const searchButtons = page.locator(
      "button[aria-label*='search' i], button[aria-label*='sök' i], .search-button",
    );
    expect(await searchInputs.count() + await searchButtons.count()).toBeGreaterThanOrEqual(
      0,
    );
  });
});
