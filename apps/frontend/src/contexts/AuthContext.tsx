import React, { createContext, useContext, useState, useEffect } from "react";
import { createTokenStorage } from '@stipendariet/api-client';

export type { User } from '@stipendariet/types';

// Auth state
interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

// Auth context value
interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<{ error?: string }>;
  loginWithGoogle: () => Promise<{ error?: string }>;
  signup: (email: string, password: string, name?: string) => Promise<{ error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// API base URL - configure for your backend
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const accessTokenStorage = createTokenStorage('auth_access_token');
const refreshTokenStorage = createTokenStorage('auth_refresh_token');

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch current user from backend
  const fetchCurrentUser = async (): Promise<User | null> => {
    const token = accessTokenStorage.get();
    if (!token) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          accessTokenStorage.clear();
          refreshTokenStorage.clear();
          return null;
        }
        throw new Error("Failed to fetch user");
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching current user:", error);
      return null;
    }
  };

  // Refresh user data
  const refreshUser = async () => {
    const userData = await fetchCurrentUser();
    setUser(userData);
  };

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      const userData = await fetchCurrentUser();
      setUser(userData);
      setIsLoading(false);
    };

    initAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Login with email/password
  const login = async (email: string, password: string): Promise<{ error?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { error: errorData.message || "Inloggningen misslyckades" };
      }

      const data = await response.json();
      accessTokenStorage.set(data.access_token);
      if (data.refresh_token) refreshTokenStorage.set(data.refresh_token);
      setUser(data.user);
      return {};
    } catch (error) {
      console.error("Login error:", error);
      return { error: "Ett fel uppstod vid inloggning" };
    }
  };

  // Login with Google (redirect-based)
  const loginWithGoogle = async (): Promise<{ error?: string }> => {
    try {
      // Redirect to your backend's Google OAuth endpoint
      // The backend should handle the OAuth flow and redirect back with tokens
      window.location.href = `${API_BASE_URL}/auth/google`;
      return {};
    } catch (error) {
      console.error("Google login error:", error);
      return { error: "Google-inloggning misslyckades" };
    }
  };

  // Signup with email/password
  const signup = async (email: string, password: string, name?: string): Promise<{ error?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password, name }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { error: errorData.message || "Registreringen misslyckades" };
      }

      const data = await response.json();
      
      // If your backend returns tokens on signup, store them
      if (data.access_token) {
        accessTokenStorage.set(data.access_token);
        if (data.refresh_token) refreshTokenStorage.set(data.refresh_token);
        setUser(data.user);
      }
      
      return {};
    } catch (error) {
      console.error("Signup error:", error);
      return { error: "Ett fel uppstod vid registrering" };
    }
  };

  // Logout
  const logout = async () => {
    try {
      const token = accessTokenStorage.get();
      if (token) {
        // Optionally notify backend about logout
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }).catch(() => {
          // Ignore logout errors - we'll clear local state anyway
        });
      }
    } finally {
      accessTokenStorage.clear();
      refreshTokenStorage.clear();
      setUser(null);
    }
  };

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    loginWithGoogle,
    signup,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Helper to get access token for API calls
export function getAuthToken(): string | null {
  return createTokenStorage('auth_access_token').get();
}
