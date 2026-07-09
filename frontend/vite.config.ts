import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@sample-tickets": path.resolve(__dirname, "../sample-tickets/tickets.json")
    }
  },
  server: {
    fs: {
      allow: [path.resolve(__dirname, ".."), path.resolve(__dirname, "../sample-tickets")]
    }
  }
});
