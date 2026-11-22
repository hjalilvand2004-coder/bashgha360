import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// RTL Persian app — dev server on 3000 (sandbox preview), API proxied to FastAPI.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
