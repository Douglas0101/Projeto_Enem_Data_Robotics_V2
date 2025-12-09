import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "buffer/": "buffer",
    },
  },
  define: {
    "global": "window",
  },
  server: {
    port: 5173,
    allowedHosts: true,
    proxy: {
      "/v1": {
        target: process.env.API_TARGET || "http://localhost:8000",
        changeOrigin: true
      },
      "/auth": {
        target: process.env.API_TARGET || "http://localhost:8000",
        changeOrigin: true
      },
      "/health": {
        target: process.env.API_TARGET || "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  optimizeDeps: {
    include: ["highcharts", "highcharts-react-official", "plotly.js", "react-plotly.js", "@chakra-ui/react", "@emotion/react", "@emotion/styled", "framer-motion", "buffer"]
  }
});