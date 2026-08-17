import { defineConfig, devices } from "@playwright/test";

/**
 * PWA verification (US7 / SC-006 / Principle V).
 *
 * Runs against a production build, not `next dev`: the service worker and the
 * manifest are what ship, and dev-server behaviour differs enough that a passing
 * dev run would not prove SC-006.
 *
 * Set PW_CHROMIUM_PATH to use a preinstalled Chromium instead of Playwright's own
 * download (used by sandboxes and images that ship the browser separately).
 */
const port = Number(process.env.PW_PORT ?? 3100);

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? "line" : "list",
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${port}`,
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
    launchOptions: process.env.PW_CHROMIUM_PATH
      ? { executablePath: process.env.PW_CHROMIUM_PATH }
      : {},
  },
  webServer: {
    command: `npm run build && npx next start -p ${port}`,
    url: `http://localhost:${port}/login`,
    reuseExistingServer: !process.env.CI,
    timeout: 300_000,
  },
});
