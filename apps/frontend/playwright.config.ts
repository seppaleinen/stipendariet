import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E tests for the frontend.
 *
 * Local dev:  `pnpm --filter @stipendariet/frontend test:e2e`
 *             (starts Vite dev server on port 8080)
 * CI:         starts the Docker container or dev server
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: "./e2e",

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail CI if test.only was left in */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* One worker on CI, parallel locally */
  workers: process.env.CI ? 1 : undefined,

  /* HTML report */
  reporter: "html",

  /* Shared settings */
  use: {
    /* Frontend dev server runs on 8080 (see vite.config.ts) */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:8080",

    /* Collect trace on first retry for debugging */
    trace: "on-first-retry",
  },

  /* Browser matrix */
  projects: [
    {
      name: "setup",
      testMatch: ["auth.setup.ts"],
    },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: "./e2e/auth.json" },
      dependencies: ["setup"],
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"], storageState: "./e2e/auth.json" },
      dependencies: ["setup"],
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"], storageState: "./e2e/auth.json" },
      dependencies: ["setup"],
    },
  ],
});
