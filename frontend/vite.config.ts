import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Dev mode: forward all API calls to FastAPI backend
      "/run-pipeline":  { target: "http://localhost:8000", changeOrigin: true },
      "/approve-spec":  { target: "http://localhost:8000", changeOrigin: true },
      "/cancel":        { target: "http://localhost:8000", changeOrigin: true },
      "/status":        { target: "http://localhost:8000", changeOrigin: true },
      "/stream":        { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
