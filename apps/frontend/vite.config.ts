import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    watch: {
      usePolling: true,
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(
    Boolean,
  ),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // NOTE: `build.ssr` is intentionally NOT set here — it would force the entire
  // client build into SSR mode. The SSR bundle is built separately by
  // scripts/prerender.js via Vite's programmatic API:
  //   createViteServer({ build: { ssr: true, rollupOptions: { input: "src/entry-server.tsx" } } })
}));
