// ── @stipendariet/api-client auth helpers ──────────────────────────────
// Zero-dependency token utilities shared between apps/frontend and apps/admin.
// All localStorage access is guarded for SSR (typeof window === 'undefined').

export interface TokenPayload {
  sub?: string;
  email?: string;
  name?: string;
  role?: string;
  exp?: number;
  [key: string]: unknown;
}

export interface TokenStorage {
  get(): string | null;
  set(token: string): void;
  clear(): void;
}

export function createTokenStorage(key: string): TokenStorage {
  return {
    get(): string | null {
      if (typeof window === 'undefined') return null;
      try {
        return localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    set(token: string): void {
      if (typeof window === 'undefined') return;
      try {
        localStorage.setItem(key, token);
      } catch {}
    },
    clear(): void {
      if (typeof window === 'undefined') return;
      try {
        localStorage.removeItem(key);
      } catch {}
    },
  };
}

export function decodeTokenPayload(token: string | null | undefined): TokenPayload | null {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const payloadPart = parts[1];
  if (!payloadPart) return null;
  try {
    const base64url = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const padding = '='.repeat((4 - (base64url.length % 4)) % 4);
    const json = atob(base64url + padding);
    return JSON.parse(json) as TokenPayload;
  } catch {
    return null;
  }
}

export function isTokenExpired(
  token: string | null | undefined,
  thresholdMs: number = 0,
): boolean {
  const payload = decodeTokenPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  const expiryMs = payload.exp * 1000;
  const now = Date.now();
  return expiryMs <= now + thresholdMs;
}

// Backward-compatible helper for apps/frontend.
// Reads the access token from localStorage (SSR-safe).
export function getAuthToken(): string | null {
  return createTokenStorage('auth_access_token').get();
}