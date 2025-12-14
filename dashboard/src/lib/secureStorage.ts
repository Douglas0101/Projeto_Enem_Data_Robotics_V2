/**
 * Secure Storage Module
 * 
 * Centraliza o gerenciamento de tokens de autenticação usando sessionStorage
 * em vez de localStorage para maior segurança contra ataques XSS.
 * 
 * sessionStorage é preferível porque:
 * - Dados são limpos quando a aba/janela é fechada
 * - Não é compartilhado entre abas (isolamento)
 * - Reduz superfície de ataque para scripts maliciosos
 */

const TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

/**
 * Armazena o token de acesso de forma segura
 */
export function setAccessToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

/**
 * Recupera o token de acesso
 */
export function getAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

/**
 * Armazena o refresh token
 */
export function setRefreshToken(token: string): void {
  sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
}

/**
 * Recupera o refresh token
 */
export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Limpa todos os tokens de autenticação
 */
export function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Armazena ambos os tokens de uma vez (conveniência para login)
 */
export function setTokens(accessToken: string, refreshToken: string): void {
  setAccessToken(accessToken);
  setRefreshToken(refreshToken);
}

/**
 * Verifica se existe um token de acesso armazenado
 */
export function hasAccessToken(): boolean {
  return getAccessToken() !== null;
}

// Export default object for backward compatibility
export const secureStorage = {
  setAccessToken,
  getAccessToken,
  setRefreshToken,
  getRefreshToken,
  clearTokens,
  setTokens,
  hasAccessToken,
};

export default secureStorage;
