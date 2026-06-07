import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: [".trunk/**/*"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: [
        "src/lib/utils.ts",
        "src/lib/page-metadata.ts",
        "src/hooks/use-mobile.tsx",
        "src/hooks/usePremiumStatus.ts",
      ],
      thresholds: {
        lines: 80,
        branches: 75,
        functions: 85,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
