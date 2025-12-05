import { toast } from "sonner";

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
  
  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      ...init
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
      
      // Lança erro específico para a UI cancelar loadings
      throw new ApiError(429, "RATE_LIMIT_EXCEEDED");
    }

    if (!response.ok) {
      // 2. Interceptor Inteligente de Erros (JSON dentro de Blob)
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

    // 3. Detecção Automática de Binários (PDF/Excel/CSV)
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

  } catch (error: any) {
    // 4. Tratamento de Falha de Rede
    if (error instanceof TypeError && error.message === "Failed to fetch") {
        toast.error("Sem Conexão", {
            description: "Não foi possível contatar o servidor. Verifique se o backend está rodando."
        });
    }
    throw error;
  }
}

export const apiClient = {
  get: <T>(path: string, headers?: HeadersInit) => request<T>(path, { method: 'GET', headers }),
  post: <T>(path: string, body: any) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  // Método explícito para downloads se preferir tipagem forte
  download: async (path: string) => request<Blob>(path) 
};