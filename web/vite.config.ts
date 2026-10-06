import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The build lands inside the Python package so `python -m monay` (and the
// PyInstaller binary) can serve it. `npm run dev` proxies /api to a running
// `python -m monay` (MONAY_NO_BROWSER=1 recommended).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../monay/web/static",
    emptyOutDir: true,
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
});
