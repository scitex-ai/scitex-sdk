import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/browser",
  testMatch: ["app-header.spec.ts", "filter-field.spec.ts", "shell-frame.spec.ts", "project-view-context.spec.ts"],
  fullyParallel: true,
  workers: process.env.CI ? 2 : undefined,
  use: {
    browserName: "chromium",
    launchOptions: process.env.SCITEX_TEST_CHROMIUM
      ? { executablePath: process.env.SCITEX_TEST_CHROMIUM }
      : {},
  },
});
