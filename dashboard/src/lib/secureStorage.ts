/**
 * Secure Storage Module
 * 
 * Centraliza o gerenciamento de tokens de autenticação usando sessionStorage
 * com criptografia AES-GCM 256-bit para proteção contra ataques XSS.
 * 
 * Security layers:
 * 1. sessionStorage (dados limpos ao fechar aba)
 * 2. AES-GCM 256-bit encryption (tokens não legíveis em texto plano)
 * 3. Fallback graceful (degrada para texto plano se crypto falhar)
 */

import { encrypt, decrypt, isCryptoSupported } from "./crypto";

const TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const ENCRYPTED_PREFIX = "enc:"; // Prefix to identify encrypted values

/**
 * Checks if a stored value is encrypted (has the enc: prefix)
 */
function isEncrypted(value: string): boolean {
  return value.startsWith(ENCRYPTED_PREFIX);
}

/**
 * Armazena o token de acesso de forma segura (criptografado)
 */
export async function setAccessToken(token: string): Promise<void> {
  try {
    if (isCryptoSupported()) {
      const encrypted = await encrypt(token);
      sessionStorage.setItem(TOKEN_KEY, ENCRYPTED_PREFIX + encrypted);
    } else {
      // Fallback: plain text (browsers antigos)
      sessionStorage.setItem(TOKEN_KEY, token);
    }
  } catch (error) {
    if (import.meta.env.DEV) console.warn("[SecureStorage] Encryption failed");
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

/**
 * Recupera o token de acesso (descriptografado)
 */
export async function getAccessToken(): Promise<string | null> {
  const stored = sessionStorage.getItem(TOKEN_KEY);
  if (!stored) return null;

  try {
    if (isEncrypted(stored)) {
      const ciphertext = stored.slice(ENCRYPTED_PREFIX.length);
      return await decrypt(ciphertext);
    }
    // Fallback: valor não criptografado (migração)
    return stored;
  } catch (error) {
    if (import.meta.env.DEV) console.warn("[SecureStorage] Decryption failed");
    // Token corrupto ou chave mudou - limpar para forçar re-login
    clearTokens();
    return null;
  }
}

/**
 * Versão síncrona para compatibilidade com código existente.
 * AVISO: Retorna null se o token estiver criptografado e precisa de async.
 * Use getAccessToken() (async) quando possível.
 */
export function getAccessTokenSync(): string | null {
  const stored = sessionStorage.getItem(TOKEN_KEY);
  if (!stored) return null;
  
  // Se está criptografado, não pode descriptografar de forma síncrona
  if (isEncrypted(stored)) {
    if (import.meta.env.DEV) console.warn("[SecureStorage] Sync access to encrypted token");
    return null;
  }
  return stored;
}

/**
 * Armazena o refresh token de forma segura (criptografado)
 */
export async function setRefreshToken(token: string): Promise<void> {
  try {
    if (isCryptoSupported()) {
      const encrypted = await encrypt(token);
      sessionStorage.setItem(REFRESH_TOKEN_KEY, ENCRYPTED_PREFIX + encrypted);
    } else {
      sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
    }
  } catch (error) {
    if (import.meta.env.DEV) console.warn("[SecureStorage] Encryption failed");
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

/**
 * Recupera o refresh token (descriptografado)
 */
export async function getRefreshToken(): Promise<string | null> {
  const stored = sessionStorage.getItem(REFRESH_TOKEN_KEY);
  if (!stored) return null;

  try {
    if (isEncrypted(stored)) {
      const ciphertext = stored.slice(ENCRYPTED_PREFIX.length);
      return await decrypt(ciphertext);
    }
    return stored;
  } catch (error) {
    if (import.meta.env.DEV) console.warn("[SecureStorage] Decryption failed");
    clearTokens();
    return null;
  }
}

/**
 * Limpa todos os tokens de autenticação (síncrono)
 */
export function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Armazena ambos os tokens de uma vez (conveniência para login)
 */
export async function setTokens(accessToken: string, refreshToken: string): Promise<void> {
  await Promise.all([
    setAccessToken(accessToken),
    setRefreshToken(refreshToken),
  ]);
}

/**
 * Verifica se existe um token de acesso armazenado (síncrono)
 */
export function hasAccessToken(): boolean {
  return sessionStorage.getItem(TOKEN_KEY) !== null;
}

// Export default object for backward compatibility
export const secureStorage = {
  setAccessToken,
  getAccessToken,
  getAccessTokenSync,
  setRefreshToken,
  getRefreshToken,
  clearTokens,
  setTokens,
  hasAccessToken,
};

export default secureStorage;
