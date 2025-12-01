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
    proxy: {
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  optimizeDeps: {
    include: ["highcharts", "highcharts-react-official", "plotly.js", "react-plotly.js", "@chakra-ui/react", "@emotion/react", "@emotion/styled", "framer-motion", "buffer"]
  }
});

