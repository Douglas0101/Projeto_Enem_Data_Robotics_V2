import { defineConfig, devices } from '@playwright/test';

console.log('Playwright Config - CI_DOCKER:', process.env.CI_DOCKER);
console.log('Playwright Config - BASE_URL:', process.env.BASE_URL);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  timeout: 30000,
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Only start webServer if NOT running in Docker orchestration
  webServer: process.env.CI_DOCKER ? undefined : {
    command: 'npm run dev:frontend',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
