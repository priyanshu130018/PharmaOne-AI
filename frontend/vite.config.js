import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The app talks to the API via the relative path `/api` so the exact backend
// host/port never needs to be baked into the bundle. In production nginx proxies
// `/api` to the backend container; in local dev Vite proxies it (see below).
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
