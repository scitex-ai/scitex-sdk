import { defineConfig } from "vitest/config";

// tests/scitex_sdk/ui/ts/*.test.ts are plain Node scripts (node --experimental-strip-types);
// vitest owns only tests/scitex_sdk/ui/vitest/.
export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/scitex_sdk/ui/vitest/**/*.test.ts"],
  },
});
