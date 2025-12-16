import React, { useState, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { apiClient } from "../api/client";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "../components/ui/card";
import { Link, useNavigate } from "react-router-dom";

/**
 * Sanitizes user input to prevent XSS and injection attacks.
 */
function sanitizeInput(input: string): string {
  return input.trim().replace(/[<>]/g, "");
}

/**
 * Calculates password strength score (0-4).
 */
function calculatePasswordStrength(password: string): number {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  return Math.min(score, 4);
}

/**
 * Returns password strength label and color.
 */
function getPasswordStrengthInfo(score: number): { label: string; color: string } {
  const levels = [
    { label: "Muito fraca", color: "bg-red-500" },
    { label: "Fraca", color: "bg-orange-500" },
    { label: "Média", color: "bg-yellow-500" },
    { label: "Forte", color: "bg-lime-500" },
    { label: "Muito forte", color: "bg-green-500" },
  ];
  return levels[score] || levels[0];
}

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showStrength, setShowStrength] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const passwordStrength = useMemo(() => calculatePasswordStrength(password), [password]);
  const strengthInfo = useMemo(() => getPasswordStrengthInfo(passwordStrength), [passwordStrength]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // Sanitize inputs before sending to API
    const sanitizedEmail = sanitizeInput(email);
    const sanitizedPassword = password; // Password not trimmed to preserve spaces

    try {
      const response = await apiClient.post<{
        access_token: string;
        refresh_token: string;
        token_type: string;
      }>("/auth/login", { email: sanitizedEmail, password: sanitizedPassword });

      await login(response.access_token, response.refresh_token);
      toast.success("Bem-vindo de volta!");
      navigate("/dashboard");
    } catch (error: unknown) {
      // Tipagem segura do erro
      const isApiError = error instanceof Error && 'status' in error;
      const status = isApiError ? (error as { status: number }).status : 0;
      const message = error instanceof Error ? error.message : "Erro desconhecido";
      
      if (status === 401) {
        toast.error("Credenciais Inválidas", {
          description: message || "E-mail ou senha incorretos.",
        });
      } else if (status === 429) {
        // Rate limit - toast já exibido pelo client.ts
      } else {
        // Erro inesperado (rede, servidor, etc)
        toast.error("Falha no Login", {
          description: "Não foi possível conectar ao servidor. Tente novamente.",
        });
      }
      // Logs removidos completamente para segurança (nem em DEV)
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 py-12 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Entrar no ENEM Data</CardTitle>
          <CardDescription className="text-center">
            Digite seu e-mail e senha para acessar o dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">E-mail</label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">Senha</label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setShowStrength(true)}
                onBlur={() => setShowStrength(false)}
                required
                disabled={isLoading}
                autoComplete="current-password"
              />
              {/* Password Strength Indicator */}
              {showStrength && password.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="flex gap-1">
                    {[0, 1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-all ${
                          i < passwordStrength ? strengthInfo.color : "bg-zinc-200"
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Força: <span className="font-medium">{strengthInfo.label}</span>
                  </p>
                </div>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col space-y-2">
          <div className="text-sm text-center text-muted-foreground">
            Não tem uma conta?{" "}
            <Link to="/signup" className="text-primary hover:underline font-medium">
              Cadastre-se
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
