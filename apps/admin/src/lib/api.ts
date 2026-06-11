import { createApiClient, ApiError } from '@stipendariet/api-client';

const backendBase = (import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

const rawApi = createApiClient({
  baseUrl: backendBase,
  getToken: () => localStorage.getItem('adminToken'),
});

// Wrap to provide { data } response shape (axios-compatible) and 401 redirect
async function wrap<T>(promise: Promise<{ data: T; status: number; ok: boolean }>): Promise<{ data: T }> {
  try {
    const result = await promise;
    return { data: result.data };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      localStorage.removeItem('adminToken');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    throw error;
  }
}

// Axios-compatible API surface — callers use `backendApi.get/post/put/patch`
// with the familiar `response.data` pattern
export const backendApi = {
  get: <T>(url: string, config?: { params?: Record<string, string | number | undefined> }) =>
    wrap(rawApi.get<T>(url, config?.params)),
  post: <T>(url: string, data?: unknown) =>
    wrap(rawApi.post<T>(url, data)),
  put: <T>(url: string, data?: unknown) =>
    wrap(rawApi.put<T>(url, data)),
  patch: <T>(url: string, data?: unknown) =>
    wrap(rawApi.patch<T>(url, data)),
};
