import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Resolve the "@/*" alias from tsconfig.json (built into Vite 8).
    tsconfigPaths: true,
  },
  test: {
    environment: "node",
  },
});
