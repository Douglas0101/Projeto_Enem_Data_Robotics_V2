import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { apiClient } from "../api/client";
import { toast } from "sonner";

interface User {
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    setIsAuthenticated(false);
    toast.info("Você foi desconectado.");
  }, []);

  const login = useCallback((token: string, refreshToken: string) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("refresh_token", refreshToken);
    setIsAuthenticated(true);
    
    // Fetch user details immediately after login
    apiClient.get<User>("/auth/me")
      .then(setUser)
      .catch((err) => {
        console.error("Failed to fetch user profile", err);
      });
  }, []);

  useEffect(() => {
    // Listen for 401 events from api client
    const handleAuthLogout = () => logout();
    window.addEventListener("auth:logout", handleAuthLogout);

    const token = localStorage.getItem("access_token");
    if (token) {
      // Optional: Validate token with /me endpoint
      apiClient.get<User>("/auth/me")
        .then((userData) => {
          setUser(userData);
          setIsAuthenticated(true);
        })
        .catch(() => {
          logout();
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }

    return () => {
      window.removeEventListener("auth:logout", handleAuthLogout);
    };
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};