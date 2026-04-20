import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5900,
    proxy: {
      "/api":      { target: "http://localhost:8900", changeOrigin: true },
      "/runs":     { target: "http://localhost:8900", changeOrigin: true },
      "/sessions": { target: "http://localhost:8900", changeOrigin: true },
      "/swarm":    { target: "http://localhost:8900", changeOrigin: true },
      "/system":   { target: "http://localhost:8900", changeOrigin: true },
      "/upload":   { target: "http://localhost:8900", changeOrigin: true },
      "/health":   { target: "http://localhost:8900", changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-charts": ["echarts"],
        },
      },
    },
  },
});
