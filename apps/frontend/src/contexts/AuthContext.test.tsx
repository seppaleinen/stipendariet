import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import { AuthProvider, useAuth, User } from "./AuthContext";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// Mock react-router-dom
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/" }),
  Outlet: () => null,
  Routes: () => null,
  Route: () => null,
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock react-helmet-async
vi.mock("react-helmet-async", () => ({
  HelmetProvider: ({ children }: { children: React.ReactNode }) => children,
  Helmet: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
const mockIntersectionObserver = vi.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
global.IntersectionObserver = mockIntersectionObserver;

// Helper to render with AuthProvider
function renderWithAuthProvider(
  ui: React.ReactNode,
  initialUser: User | null = null,
  initialToken: string | null = null
) {
  // Setup localStorage mock based on test params
  localStorageMock.getItem.mockImplementation((key: string) => {
    if (key === "auth_access_token") return initialToken;
    return null;
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  return render(ui, { wrapper });
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
  });

  describe("AuthProvider initialization", () => {
    it("initializes with null user when no token", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, null, null);
      });

      expect(authState.user).toBeNull();
      expect(authState.isLoading).toBe(false);
      expect(authState.isAuthenticated).toBe(false);
    });

    it("loads user from localStorage when token exists", async () => {
      const mockUser: User = { id: "1", email: "test@example.com", name: "Test User" };
      localStorageMock.getItem.mockImplementation((key: string) => {
        if (key === "auth_access_token") return "mock-token";
        return null;
      });

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockUser,
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, mockUser, "mock-token");
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/me"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-token",
          }),
        })
      );
      expect(authState.user).toEqual(mockUser);
      expect(authState.isAuthenticated).toBe(true);
    });

    it("clears tokens and sets user null on 401", async () => {
      localStorageMock.getItem.mockReturnValue("expired-token");

      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({}),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, null, "expired-token");
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("auth_access_token");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("auth_refresh_token");
      expect(authState.user).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });

    it("handles fetch error gracefully", async () => {
      localStorageMock.getItem.mockReturnValue("some-token");

      mockFetch.mockRejectedValue(new Error("Network error"));

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, null, "some-token");
      });

      expect(authState.user).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });
  });

  describe("login()", () => {
    it("successful login stores tokens and sets user", async () => {
      const mockUser: User = { id: "2", email: "user@example.com", name: "User" };
      const mockTokens = { access_token: "new-access", refresh_token: "new-refresh" };

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ ...mockTokens, user: mockUser }),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.login("user@example.com", "password123");
        expect(result).toEqual({});
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/login"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({ email: "user@example.com", password: "password123" }),
        })
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith("auth_access_token", "new-access");
      expect(localStorageMock.setItem).toHaveBeenCalledWith("auth_refresh_token", "new-refresh");
      expect(authState.user).toEqual(mockUser);
      expect(authState.isAuthenticated).toBe(true);
    });

    it("failed login returns error message", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ message: "Invalid credentials" }),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.login("wrong@example.com", "wrong");
        expect(result).toEqual({ error: "Invalid credentials" });
      });
    });

    it("handles network error and returns Swedish error message", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.login("user@example.com", "pass");
        expect(result).toEqual({ error: "Ett fel uppstod vid inloggning" });
      });
    });

    it("handles response without message field", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({}),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.login("user@example.com", "pass");
        expect(result).toEqual({ error: "Inloggningen misslyckades" });
      });
    });
  });

  describe("logout()", () => {
    it("clears tokens and sets user null", async () => {
      localStorageMock.getItem.mockReturnValue("some-token");

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, { id: "1", email: "test@example.com" }, "some-token");
      });

      await act(async () => {
        await authState.logout();
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("auth_access_token");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("auth_refresh_token");
      expect(authState.user).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });

    it("attempts to notify backend on logout but ignores errors", async () => {
      localStorageMock.getItem.mockReturnValue("some-token");

      mockFetch.mockRejectedValue(new Error("Backend unavailable"));

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, { id: "1", email: "test@example.com" }, "some-token");
      });

      await act(async () => {
        await authState.logout();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/logout"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            Authorization: "Bearer some-token",
          }),
        })
      );
      expect(authState.user).toBeNull();
    });

    it("does not call backend if no token", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        await authState.logout();
      });

      expect(mockFetch).not.toHaveBeenCalled();
      expect(authState.user).toBeNull();
    });
  });

  describe("signup()", () => {
    it("successful signup stores tokens when returned", async () => {
      const mockUser: User = { id: "3", email: "new@example.com", name: "New User" };
      const mockTokens = { access_token: "signup-token", refresh_token: "signup-refresh" };

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ ...mockTokens, user: mockUser }),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.signup("new@example.com", "newpass123", "New User");
        expect(result).toEqual({});
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/signup"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ email: "new@example.com", password: "newpass123", name: "New User" }),
        })
      );
      expect(authState.user).toEqual(mockUser);
      expect(authState.isAuthenticated).toBe(true);
    });

    it("successful signup without tokens does not set user", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.signup("new@example.com", "newpass123");
        expect(result).toEqual({});
      });

      expect(authState.user).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    });

    it("failed signup returns error message", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ message: "Email already exists" }),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.signup("existing@example.com", "pass");
        expect(result).toEqual({ error: "Email already exists" });
      });
    });

    it("handles network error", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.signup("new@example.com", "pass");
        expect(result).toEqual({ error: "Ett fel uppstod vid registrering" });
      });
    });
  });

  describe("refreshUser()", () => {
    it("refreshes user data from API", async () => {
      const mockUser: User = { id: "5", email: "refreshed@example.com", name: "Refreshed" };

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockUser,
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, null, "refresh-token");
      });

      await act(async () => {
        await authState.refreshUser();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/me"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer refresh-token",
          }),
        })
      );
      expect(authState.user).toEqual(mockUser);
    });

    it("handles 401 during refresh", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({}),
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />, null, "expired-token");
      });

      await act(async () => {
        await authState.refreshUser();
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("auth_access_token");
      expect(authState.user).toBeNull();
    });
  });

  describe("loginWithGoogle()", () => {
    it("redirects to Google OAuth endpoint", async () => {
      const originalLocation = window.location;
      const mockLocation = { href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.loginWithGoogle();
        expect(result).toEqual({});
        expect(mockLocation.href).toContain("/auth/google");
      });

      // Restore original location
      Object.defineProperty(window, "location", {
        value: originalLocation,
        writable: true,
      });
    });

    it("handles Google login error", async () => {
      const originalLocation = window.location;
      const mockLocation = { href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
        configurable: true,
      });

      // Make location.href assignment throw
      Object.defineProperty(window, "location", {
        get() {
          return {
            get href() { return mockLocation.href; },
            set href(val: string) { mockLocation.href = val; throw new Error("Redirect failed"); },
          };
        },
        configurable: true,
      });

      let authState: any;
      const TestComponent = () => {
        authState = useAuth();
        return null;
      };

      await act(async () => {
        renderWithAuthProvider(<TestComponent />);
      });

      await act(async () => {
        const result = await authState.loginWithGoogle();
        expect(result).toEqual({ error: "Google-inloggning misslyckades" });
      });

      Object.defineProperty(window, "location", {
        value: originalLocation,
        writable: true,
      });
    });
  });

  describe("useAuth() error handling", () => {
    it("throws error when used outside AuthProvider", () => {
      const TestComponent = () => {
        expect(() => useAuth()).toThrow("useAuth must be used within an AuthProvider");
        return null;
      };

      render(<TestComponent />);
    });
  });
});
