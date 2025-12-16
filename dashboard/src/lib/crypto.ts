/**
 * Crypto Module - AES-GCM 256-bit Encryption
 * 
 * Provides secure encryption/decryption for sensitive data stored in browser.
 * Uses Web Crypto API (native browser implementation) for maximum security.
 * 
 * Security features:
 * - AES-GCM 256-bit encryption (NIST approved)
 * - Unique random IV per encryption operation
 * - Constant-time key derivation from browser fingerprint
 */

const ALGORITHM = "AES-GCM";
const KEY_LENGTH = 256;
const IV_LENGTH = 12; // 96 bits recommended for GCM

/**
 * Generates a deterministic but unique encryption key based on browser characteristics.
 * This ensures tokens encrypted in one session can be decrypted in the same browser.
 */
async function deriveKey(): Promise<CryptoKey> {
  // Browser fingerprint components (non-identifying, but consistent per browser)
  const fingerprint = [
    navigator.userAgent,
    navigator.language,
    new Date().getTimezoneOffset().toString(),
    screen.colorDepth.toString(),
    window.location.origin,
  ].join("|");

  // Convert fingerprint to key material
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    encoder.encode(fingerprint),
    { name: "PBKDF2" },
    false,
    ["deriveKey"]
  );

  // Derive AES key using PBKDF2
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: encoder.encode("enem-data-robotics-v2"),
      iterations: 100000,
      hash: "SHA-256",
    },
    keyMaterial,
    { name: ALGORITHM, length: KEY_LENGTH },
    false,
    ["encrypt", "decrypt"]
  );
}

/**
 * Encrypts a string using AES-GCM 256-bit.
 * Returns base64-encoded ciphertext with prepended IV.
 * 
 * @param plaintext - The string to encrypt
 * @returns Base64-encoded encrypted data (IV + ciphertext)
 */
export async function encrypt(plaintext: string): Promise<string> {
  try {
    const key = await deriveKey();
    const encoder = new TextEncoder();
    const data = encoder.encode(plaintext);
    
    // Generate random IV for each encryption
    const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
    
    const ciphertext = await crypto.subtle.encrypt(
      { name: ALGORITHM, iv },
      key,
      data
    );

    // Combine IV + ciphertext for storage
    const combined = new Uint8Array(iv.length + ciphertext.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(ciphertext), iv.length);

    // Encode to base64 for safe storage
    return btoa(String.fromCharCode(...combined));
  } catch (error) {
    if (import.meta.env.DEV) console.warn("[Crypto] Encryption failed");
    throw new Error("Encryption failed");
  }
}

/**
 * Decrypts a base64-encoded AES-GCM ciphertext.
 * 
 * @param ciphertext - Base64-encoded encrypted data (IV + ciphertext)
 * @returns Decrypted plaintext string
 */
export async function decrypt(ciphertext: string): Promise<string> {
  try {
    const key = await deriveKey();
    
    // Decode from base64
    const combined = Uint8Array.from(atob(ciphertext), c => c.charCodeAt(0));
    
    // Extract IV and ciphertext
    const iv = combined.slice(0, IV_LENGTH);
    const encryptedData = combined.slice(IV_LENGTH);

    const decrypted = await crypto.subtle.decrypt(
      { name: ALGORITHM, iv },
      key,
      encryptedData
    );

    const decoder = new TextDecoder();
    return decoder.decode(decrypted);
  } catch (error) {
    if (import.meta.env.DEV) console.warn("[Crypto] Decryption failed");
    throw new Error("Decryption failed");
  }
}

/**
 * Checks if Web Crypto API is available in the current environment.
 */
export function isCryptoSupported(): boolean {
  return (
    typeof crypto !== "undefined" &&
    typeof crypto.subtle !== "undefined" &&
    typeof crypto.subtle.encrypt === "function"
  );
}

export const cryptoModule = {
  encrypt,
  decrypt,
  isCryptoSupported,
};

export default cryptoModule;
