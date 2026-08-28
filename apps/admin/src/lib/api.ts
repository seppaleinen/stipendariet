// ── @stipendariet/admin API client ──────────────────────────────────────
// Thin per-app client wrapping @stipendariet/api-client with 401 redirect.
//
// Exports:
//   api      — raw HttpClient from createApiClient (use for new code)
//   request  — wrapper that adds 401 redirect + { data } destructuring
//              (use for mechanical migration of existing callers)

import { createApiClient, ApiError } from '@stipendariet/api-client';
import { getAdminAuthToken } from './auth';

const baseUrl = (import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

export const api = createApiClient({
  baseUrl,
  getToken: getAdminAuthToken,
});

function handle401(error: unknown): void {
  if (error instanceof ApiError && error.status === 401) {
    localStorage.removeItem('adminToken');
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
}

/** Wraps the raw api call: adds 401 redirect and returns { data } shape (axios-compatible). */
export async function request<T>(promise: Promise<{ data: T; status: number; ok: boolean }>): Promise<{ data: T }> {
  try {
    const result = await promise;
    return { data: result.data };
  } catch (error) {
    handle401(error);
    throw error;
  }
}
