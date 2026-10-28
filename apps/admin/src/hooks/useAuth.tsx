import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { ApiError, decodeTokenPayload, isTokenExpired, createTokenStorage } from '@stipendariet/api-client';
import { apiPublic } from '@/lib/api';
import { ExchangeResponse } from '@stipendariet/types';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  isExchanging: boolean;
  exchange: () => Promise<boolean>;
  refreshToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

const REFRESH_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes
const PERIODIC_CHECK_INTERVAL_MS = 60_000; // 1 minute

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExchanging, setIsExchanging] = useState(false);

  const logout = () => {
    localStorage.removeItem('adminToken');
    setUser(null);
    const authentikLogoutUrl = import.meta.env.VITE_AUTHENTIK_LOGOUT_URL;
    if (authentikLogoutUrl && typeof window !== 'undefined') {
      window.location.href = authentikLogoutUrl;
    } else {
      window.location.href = '/login';
    }
  };

  const exchange = useCallback(async (): Promise<boolean> => {
    // Exchange via the tokenless public client (no Authorization header).
    const attempt = async (): Promise<{ ok: boolean; data: ExchangeResponse | null }> => {
      try {
        const response = await apiPublic.post<ExchangeResponse>('/auth/exchange');
        return { ok: true, data: response.data };
      } catch (error: unknown) {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          return { ok: false, data: null };
        }
        // network error or other — propagate for retry
        throw error;
      }
    };

    for (let i = 0; i < 2; i++) {
      try {
        const result = await attempt();
        if (!result.ok || !result.data) return false;

        const { access_token } = result.data;
        localStorage.setItem('adminToken', access_token);

        // Decode user from JWT (backend only returns token fields)
        const payload = decodeTokenPayload(access_token);
        if (payload) {
          setUser({
            id: payload.sub || 'admin',
            email: payload.email || '',
            name: payload.name || 'Admin User',
            role: payload.role || 'admin',
          });
        }
        return true;
      } catch {
        if (i === 1) return false;
        // retry once on network error
      }
    }
    return false;
  }, []);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    const token = localStorage.getItem('adminToken');
    if (!token) {
      return exchange();
    }
    if (isTokenExpired(token, REFRESH_THRESHOLD_MS)) {
      return exchange();
    }
    // Token is still valid — decode user from it
    const payload = decodeTokenPayload(token);
    if (payload) {
      setUser({
        id: payload.sub || 'admin',
        email: payload.email || '',
        name: payload.name || 'Admin User',
        role: payload.role || 'admin',
      });
    }
    return true;
  }, [exchange]);

  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    let active = true;

    const init = async () => {
      if (token) {
        const u = decodeTokenPayload(token);
        if (u) {
          setUser({
            id: u.sub || 'admin',
            email: u.email || '',
            name: u.name || 'Admin User',
            role: u.role || 'admin',
          });
          setIsLoading(false);
          // Proactive refresh check
          await refreshToken();
          return;
        } else {
          createTokenStorage('adminToken').clear();
        }
      }

      // Token missing or expired → auto-call exchange (ForwardAuth has already
      // authenticated the browser session at the proxy)
      setIsExchanging(true);
      const success = await exchange();
      if (!active) return;
      setIsExchanging(false);
      setIsLoading(false);
      if (!success) {
        // Exchange failed — user stays unauthenticated; LoginPage will show fallback
      }
    };

    init();
    return () => { active = false; };
  }, [exchange, refreshToken]);

  // Periodic token refresh check while mounted and user is authenticated
  useEffect(() => {
    if (!user) return;
    const intervalId = setInterval(() => {
      refreshToken();
    }, PERIODIC_CHECK_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [user, refreshToken]);

  return (
    <AuthContext.Provider value={{ user, logout, isAuthenticated: !!user, isLoading, isExchanging, exchange, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
};