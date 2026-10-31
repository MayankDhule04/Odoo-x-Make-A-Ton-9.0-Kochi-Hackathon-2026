import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router";

import { api, setAccessToken } from "../api/client.js";
import type { TokenResponse, User } from "../api/client.js";

/* ------------------------------------------------------------------ */
/*  Context shape                                                      */
/* ------------------------------------------------------------------ */

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/* ------------------------------------------------------------------ */
/*  Provider                                                           */
/* ------------------------------------------------------------------ */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  /* On mount, try to restore the session via the httpOnly refresh cookie.
     This avoids the 401-redirect dance in the API client during init. */
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const res = await fetch("/api/auth/refresh", {
          method: "POST",
          credentials: "include",
        });
        if (res.ok) {
          const data = (await res.json()) as TokenResponse;
          if (!cancelled) {
            setAccessToken(data.access_token);
            setUser(data.user);
          }
        }
      } catch {
        /* no session — stay logged out */
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api.post<TokenResponse>("/api/auth/login", {
        email,
        password,
      });
      setAccessToken(data.access_token);
      setUser(data.user);
    },
    [],
  );

  const signup = useCallback(
    async (email: string, password: string, fullName: string) => {
      const data = await api.post<TokenResponse>("/api/auth/signup", {
        email,
        password,
        full_name: fullName,
      });
      setAccessToken(data.access_token);
      setUser(data.user);
    },
    [],
  );

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    navigate("/login");
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, signup, logout }),
    [user, isLoading, login, signup, logout],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
