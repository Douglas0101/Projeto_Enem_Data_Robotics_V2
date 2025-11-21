const DEFAULT_API_BASE_URL = "http://localhost:8000";

function resolveBaseUrl(): string {
  // Em dev, o proxy do Vite cuida de /v1 e /health.
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL as string;
  }
  return DEFAULT_API_BASE_URL;
}

const API_BASE_URL = resolveBaseUrl();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(
      `Erro ao chamar API (${response.status} ${response.statusText}): ${text}`
    );
  }

  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  // espaço para POST/PUT se necessário futuramente
};

