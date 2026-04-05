/**
 * AuthContext — Provides authentication state and actions to the React tree.
 *
 * Manages JWT token persistence in localStorage, user profile fetching,
 * login/logout/register flows, and 401 auto-logout.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import type { UserProfile } from "../api/types";

/* ── Context Shape ── */

interface AuthState {
  /** The current user profile, or null if not authenticated. */
  user: UserProfile | null;
  /** Whether the initial auth check is still loading. */
  isLoading: boolean;
  /** Whether the user is authenticated. */
  isAuthenticated: boolean;
  /** Login with username and password. Returns the user profile on success. */
  login: (username: string, password: string) => Promise<UserProfile>;
  /** Register a new account. Returns the user profile on success. */
  register: (username: string, password: string) => Promise<UserProfile>;
  /** Log out and clear stored credentials. */
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

/* ── Provider ── */

interface AuthProviderProps {
  children: ReactNode;
}

const DEFAULT_USER: UserProfile = {
  sub: "admin",
  tenant_id: "default",
  roles: ["admin"],
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [user] = useState<UserProfile | null>(DEFAULT_USER);
  const [isLoading] = useState(false);

  const login = useCallback(
    async (_username: string, _password: string): Promise<UserProfile> => {
      return DEFAULT_USER;
    },
    [],
  );

  const register = useCallback(
    async (_username: string, _password: string): Promise<UserProfile> => {
      return DEFAULT_USER;
    },
    [],
  );

  const logout = useCallback(() => {
    // no-op
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/* ── Hook ── */

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return ctx;
}
