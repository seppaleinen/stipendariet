// ── @stipendariet/api-client ─────────────────────────────────────────
// Zero-dependency fetch-based HTTP client factory.
// Apps create their own client instance:
//   const api = createApiClient({ baseUrl: "/api", getToken: () => localStorage.getItem("token") })

// ── Types ─────────────────────────────────────────────────────────────

export interface ApiClientConfig {
  /** Base URL for all requests (e.g. "/api" or "https://api.example.com") */
  baseUrl: string;
  /** Function that returns the current auth token, or null if unauthenticated */
  getToken?: () => string | null;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  ok: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── HTTP method helpers ───────────────────────────────────────────────

interface HttpClient {
  get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<ApiResponse<T>>;
  post<T>(path: string, body?: unknown): Promise<ApiResponse<T>>;
  put<T>(path: string, body?: unknown): Promise<ApiResponse<T>>;
  patch<T>(path: string, body?: unknown): Promise<ApiResponse<T>>;
  del<T = void>(path: string): Promise<ApiResponse<T>>;
}

// ── Client Factory ────────────────────────────────────────────────────

export function createApiClient(config: ApiClientConfig): HttpClient {
  const { baseUrl, getToken } = config;

  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string | number | undefined>,
  ): Promise<ApiResponse<T>> {
    // Build URL with query params
    const url = new URL(`${baseUrl}${path}`, window.location.origin);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      }
    }

    // Build headers
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const token = getToken?.();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Make request
    const response = await fetch(url.toString(), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    // Parse response
    let data: T;
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      data = (await response.json()) as T;
    } else {
      data = (await response.text()) as unknown as T;
    }

    if (!response.ok) {
      const message =
        typeof data === "object" && data !== null
          ? ((data as Record<string, unknown>).detail as string) ??
            ((data as Record<string, unknown>).message as string) ??
            `HTTP ${response.status}`
          : `HTTP ${response.status}`;
      throw new ApiError(response.status, message, data);
    }

    return { data, status: response.status, ok: true };
  }

  return {
    get: <T>(path: string, params?: Record<string, string | number | undefined>) =>
      request<T>("GET", path, undefined, params),
    post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
    put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
    patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
    del: <T = void>(path: string) => request<T>("DELETE", path),
  };
}
