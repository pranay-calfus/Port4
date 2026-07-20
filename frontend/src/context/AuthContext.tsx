import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as api from "../api/client";
import { setUnauthorizedHandler } from "../api/client";
import type { UserOut } from "../api/types";

interface AuthContextValue {
  token: string | null;
  identity: UserOut | null;
  isBootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  adminLogin: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = "port4_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [identity, setIdentity] = useState<UserOut | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  const clearSession = useCallback(() => {
    setToken(null);
    setIdentity(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const applySession = useCallback((newToken: string, user: UserOut) => {
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    setIdentity(user);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!token) {
        setIsBootstrapping(false);
        return;
      }
      try {
        const user = await api.whoami(token);
        if (!cancelled) setIdentity(user);
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setIsBootstrapping(false);
      }
    }
    restore();
    return () => {
      cancelled = true;
    };
    // Only re-run on mount; token changes from login/logout are handled inline where they occur.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      applySession(res.access_token, res.user);
    },
    [applySession]
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await api.register(name, email, password);
      applySession(res.access_token, res.user);
    },
    [applySession]
  );

  const adminLogin = useCallback(
    async (email: string, password: string) => {
      const res = await api.adminLogin(email, password);
      applySession(res.access_token, res.user);
    },
    [applySession]
  );

  const value = useMemo<AuthContextValue>(
    () => ({ token, identity, isBootstrapping, login, register, adminLogin, logout: clearSession }),
    [token, identity, isBootstrapping, login, register, adminLogin, clearSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
