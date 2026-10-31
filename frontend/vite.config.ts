import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// docker-compose.yml points this at the api service. On the host the API is on localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
// File change events from Windows don't reach Linux containers, so Docker uses polling.
const usePolling = process.env.WATCH_POLLING === "true";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    watch: usePolling ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
    },
  },
});
