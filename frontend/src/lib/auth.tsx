import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, post, setAccessToken } from "./api";

export type Me = {
  id: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  university_id: string | null;
  student_ref_id: string | null;
};

type AuthState = {
  me: Me | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthState>({ me: null, loading: true, login: async () => {}, logout: async () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // silent refresh on load — access token never persisted in localStorage (ACC-15)
    fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then(async (data) => {
        if (data?.access_token) {
          setAccessToken(data.access_token);
          const m = await api<Me>("/auth/me");
          setMe(m);
        }
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await post<{ access_token: string; user: { id: string } }>("/auth/login", { username, password });
    setAccessToken(data.access_token);
    const m = await api<Me>("/auth/me");
    setMe(m);
  }, []);

  const logout = useCallback(async () => {
    await post("/auth/logout").catch(() => undefined);
    setAccessToken(null);
    setMe(null);
  }, []);

  const value = useMemo(() => ({ me, loading, login, logout }), [me, loading, login, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export const hasPerm = (me: Me | null, perm: string) => !!me?.permissions.includes(perm);
export const hasRole = (me: Me | null, role: string) => !!me?.roles.includes(role);
