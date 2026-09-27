import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In local development Vite proxies `/api` to the backend (see below).
// `VITE_DEV_API_TARGET` only affects `vite dev` and defaults to a local backend.
export default defineConfig(({ mode }) => {
  const devApiTarget = process.env.VITE_DEV_API_TARGET || "http://localhost:8000";
  return {
    plugins: [react()],
    server: {
      port: Number(process.env.VITE_DEV_PORT) || 5173,
      proxy: {
        "/api": {
          target: devApiTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: "0.0.0.0",
      port: Number(process.env.FRONTEND_PORT) || 8080,
      strictPort: true,
    },
    build: {
      outDir: "dist",
      sourcemap: mode !== "production",
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/test/setup.js",
    },
  };
});
