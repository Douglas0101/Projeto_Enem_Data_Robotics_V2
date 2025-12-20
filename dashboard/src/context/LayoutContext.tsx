import React, { createContext, useContext, useState, useEffect } from "react";

interface LayoutContextType {
  // Sidebar (vertical)
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  // FilterBar (horizontal)
  isFilterBarCollapsed: boolean;
  toggleFilterBar: () => void;
}

const LayoutContext = createContext<LayoutContextType | undefined>(undefined);

export function LayoutProvider({ children }: { children: React.ReactNode }) {
  const [isSidebarCollapsed, setSidebarState] = useState(false);
  const [isFilterBarCollapsed, setFilterBarState] = useState(false);

  // Persistir preferências do usuário
  useEffect(() => {
    const savedSidebar = localStorage.getItem("sidebar-collapsed");
    if (savedSidebar) {
      setSidebarState(savedSidebar === "true");
    }
    const savedFilterBar = localStorage.getItem("filterbar-collapsed");
    if (savedFilterBar) {
      setFilterBarState(savedFilterBar === "true");
    }
  }, []);

  const toggleSidebar = () => {
    const newState = !isSidebarCollapsed;
    setSidebarState(newState);
    localStorage.setItem("sidebar-collapsed", String(newState));
  };

  const setSidebarCollapsed = (value: boolean) => {
    setSidebarState(value);
    localStorage.setItem("sidebar-collapsed", String(value));
  };

  const toggleFilterBar = () => {
    const newState = !isFilterBarCollapsed;
    setFilterBarState(newState);
    localStorage.setItem("filterbar-collapsed", String(newState));
  };

  return (
    <LayoutContext.Provider
      value={{
        isSidebarCollapsed,
        toggleSidebar,
        setSidebarCollapsed,
        isFilterBarCollapsed,
        toggleFilterBar,
      }}
    >
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayout() {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error("useLayout must be used within a LayoutProvider");
  }
  return context;
}
