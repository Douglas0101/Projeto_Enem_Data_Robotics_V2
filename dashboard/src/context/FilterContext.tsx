import React, { createContext, useContext, useState, useEffect } from "react";

interface FilterContextType {
  year: number;
  setYear: (year: number) => void;
  uf: string;
  setUf: (uf: string) => void;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export function FilterProvider({ children }: { children: React.ReactNode }) {
  // Tentar ler da URL ou localStorage no futuro. Por enquanto, defaults.
  const [year, setYear] = useState(2024);
  const [uf, setUf] = useState<string>("all");

  return (
    <FilterContext.Provider value={{ year, setYear, uf, setUf }}>
      {children}
    </FilterContext.Provider>
  );
}

export function useFilters() {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error("useFilters must be used within a FilterProvider");
  }
  return context;
}
