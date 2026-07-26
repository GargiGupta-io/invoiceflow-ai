import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/reviewer/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/v2": "http://127.0.0.1:8000"
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.js",
    restoreMocks: true
  }
});
