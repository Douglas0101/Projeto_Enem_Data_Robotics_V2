import { toast } from "sonner";
import { getAccessToken, clearTokens } from "@/lib/secureStorage";

const DEFAULT_API_BASE_URL = "";

function resolveBaseUrl(): string {
  // Em dev, o proxy do Vite cuida de /v1 e /health.
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL as string;
  }
  return DEFAULT_API_BASE_URL;
}

const API_BASE_URL = resolveBaseUrl();

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  
  // Inject Auth Token (via secureStorage - now async with encryption)
  const token = await getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...init,
      headers
    });

    // 1. Interceptor de Rate Limit (429) - Proteção contra DDoS
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      const msg = retryAfter 
        ? `Muitas requisições. Tente novamente em ${retryAfter}s.` 
        : "Limite de requisições excedido. Aguarde um momento.";
      
      toast.error("🚦 Tráfego Intenso", {
        description: msg,
        duration: 5000,
      });
      
      throw new ApiError(429, "RATE_LIMIT_EXCEEDED");
    }

    // 2. Interceptor de Auth (401) - Token Expirado vs Credenciais Incorretas
    if (response.status === 401) {
      // Endpoints de autenticação: 401 significa credenciais incorretas, NÃO sessão expirada
      const isAuthEndpoint = path.startsWith("/auth/login") || path.startsWith("/auth/token");
      
      if (!isAuthEndpoint) {
        // Token inválido/expirado em endpoint protegido → fazer logout
        clearTokens();
        window.dispatchEvent(new Event("auth:logout"));
        throw new ApiError(401, "Sessão expirada. Faça login novamente.");
      }
      // Para endpoints de login, extrair mensagem e lançar erro SEM toast genérico
      // LoginPage é responsável por exibir o toast com contexto apropriado
      const contentType = response.headers.get("content-type");
      let errorMessage = "Credenciais inválidas";
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      }
      throw new ApiError(401, errorMessage);
    }

    if (!response.ok) {
      // 3. Interceptor Inteligente de Erros (JSON dentro de Blob)
      const contentType = response.headers.get("content-type");
      let errorMessage = `Erro ${response.status}: ${response.statusText}`;

      // Tenta extrair mensagem detalhada do backend
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } else {
        const text = await response.text().catch(() => "");
        if (text) errorMessage = text.substring(0, 200);
      }

      toast.error("Erro na Requisição", {
        description: errorMessage
      });

      throw new ApiError(response.status, errorMessage);
    }

    // 4. Detecção Automática de Binários (PDF/Excel/CSV)
    const contentType = response.headers.get("content-type");
    if (contentType && (
        contentType.includes("application/pdf") ||
        contentType.includes("application/vnd.openxmlformats") ||
        contentType.includes("text/csv") || 
        contentType.includes("application/octet-stream")
    )) {
        return (await response.blob()) as unknown as T;
    }

    // Padrão JSON
    if (response.status === 204) return {} as T;
    return (await response.json()) as T;

  } catch (error: unknown) {
    // Tratamento de Falha de Rede (sem logs para segurança)
    if (error instanceof TypeError && error.message === "Failed to fetch") {
        toast.error("Sem Conexão", {
            description: "Não foi possível contatar o servidor."
        });
    }
    throw error;
  }
}

export const apiClient = {
  get: <T>(path: string, headers?: HeadersInit) => request<T>(path, { method: 'GET', headers }),
  post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  // Método explícito para downloads se preferir tipagem forte
  download: async (path: string) => request<Blob>(path) 
};
