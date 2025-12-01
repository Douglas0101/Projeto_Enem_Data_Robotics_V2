import "./polyfills";
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

import { ChakraProvider, extendTheme, ThemeConfig } from "@chakra-ui/react";
import { App } from "./App";
import { LayoutProvider } from "./context/LayoutContext";
import { FilterProvider } from "./context/FilterContext";

const config: ThemeConfig = {
  initialColorMode: "light",
  useSystemColorMode: false
};

const theme = extendTheme({
  config,
  colors: {
    brand: {
      50: "#E3F2FD",
      100: "#BBDEFB",
      200: "#90CAF9",
      300: "#64B5F6",
      400: "#42A5F5",
      500: "#1E88E5",
      600: "#1976D2",
      700: "#1565C0",
      800: "#0D47A1",
      900: "#0B3C91"
    }
  },
  fonts: {
    heading:
      "'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body:
      "'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
  }
});

import { ErrorBoundary } from "./components/ErrorBoundary";

try {
  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <ErrorBoundary>
        <ChakraProvider theme={theme}>
          <LayoutProvider>
            <FilterProvider>
              <App />
            </FilterProvider>
          </LayoutProvider>
        </ChakraProvider>
      </ErrorBoundary>
    </React.StrictMode>
  );
} catch (e) {
  console.error("Failed to mount React application:", e);
}

