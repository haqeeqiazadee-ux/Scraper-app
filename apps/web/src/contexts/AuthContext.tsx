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
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { auth, onAuthFailure } from "../api/client";
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

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check if we have a stored token and try to fetch the user profile.
  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      if (!auth.isAuthenticated()) {
        setIsLoading(false);
        return;
      }
      try {
        const profile = await auth.me();
        if (!cancelled) {
          setUser(profile);
        }
      } catch {
        // Token is invalid or expired — clear it
        auth.logout();
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    checkAuth();
    return () => {
      cancelled = true;
    };
  }, []);

  // Register the 401 handler so any API call that gets a 401 logs the user out.
  useEffect(() => {
    onAuthFailure(() => {
      setUser(null);
    });
  }, []);

  const login = useCallback(
    async (username: string, password: string): Promise<UserProfile> => {
      await auth.login(username, password);
      const profile = await auth.me();
      setUser(profile);
      return profile;
    },
    [],
  );

  const register = useCallback(
    async (username: string, password: string): Promise<UserProfile> => {
      await auth.register(username, password);
      const profile = await auth.me();
      setUser(profile);
      return profile;
    },
    [],
  );

  const logout = useCallback(() => {
    auth.logout();
    setUser(null);
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
