import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Where the dev server forwards /api. The browser only ever talks to its own
// origin — in Docker nginx plays this role (docker/nginx.conf) — so the app
// needs no CORS setup and no API URL baked into the bundle.
const api = process.env.MONAY_API_URL ?? "http://127.0.0.1:8000";
const proxy = { "/api": { target: api, changeOrigin: true } };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
});
