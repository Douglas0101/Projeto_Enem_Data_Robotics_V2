import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { apiClient } from "../api/client";
import { toast } from "sonner";
import { setTokens, clearTokens, hasAccessToken, getAccessToken } from "@/lib/secureStorage";

interface User {
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken: string) => Promise<void>;
  logout: (showToast?: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback((showToast: boolean = true) => {
    // Previne toast "Você foi desconectado" quando:
    // 1. Não havia sessão real (falha de login, nunca logou)
    // 2. Logout silencioso foi solicitado (ex: refresh token expirado)
    const hadSession = hasAccessToken();
    clearTokens(); // Usa secureStorage centralizado (sessionStorage)
    setUser(null);
    setIsAuthenticated(false);
    if (showToast && hadSession) {
      toast.info("Você foi desconectado.");
    }
  }, []);

  const login = useCallback(async (token: string, refreshToken: string) => {
    await setTokens(token, refreshToken); // Async: criptografa e salva
    setIsAuthenticated(true);
    
    // Fetch user details immediately after login
    apiClient.get<User>("/auth/me")
      .then(setUser)
      .catch(() => {
        // Silently handle profile fetch failure
      });
  }, []);

  useEffect(() => {
    // Listen for 401 events from api client
    const handleAuthLogout = () => logout();
    window.addEventListener("auth:logout", handleAuthLogout);

    const checkAuth = async () => {
      const hasToken = hasAccessToken();
      if (hasToken) {
        // Optional: Validate token with /me endpoint
        try {
          const userData = await apiClient.get<User>("/auth/me");
          setUser(userData);
          setIsAuthenticated(true);
        } catch {
          logout(false); // Silent logout on token validation failure
        }
      }
      setIsLoading(false);
    };

    checkAuth();

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