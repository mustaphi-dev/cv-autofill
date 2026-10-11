import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    coverage: {
      provider: "v8",
      include: ["src/**"],
      // Spec section 14: 90% branch coverage for packages/core.
      thresholds: { branches: 90 },
    },
  },
});
