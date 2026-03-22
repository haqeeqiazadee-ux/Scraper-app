/**
 * useAuth — Convenience hook for authentication.
 *
 * Re-exports the AuthContext hook plus additional helpers
 * for login/logout form handling with loading/error state.
 */

import { useState, useCallback } from "react";
import { useAuthContext } from "../contexts/AuthContext";

export { useAuthContext } from "../contexts/AuthContext";

/**
 * Hook for handling login form submission with loading and error states.
 */
export function useLogin() {
  const { login } = useAuthContext();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await login(username, password);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Login failed. Please try again.";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [login],
  );

  return { handleLogin, isLoading, error, clearError: () => setError(null) };
}

/**
 * Hook for handling registration form submission with loading and error states.
 */
export function useRegister() {
  const { register } = useAuthContext();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = useCallback(
    async (username: string, password: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await register(username, password);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Registration failed. Please try again.";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [register],
  );

  return {
    handleRegister,
    isLoading,
    error,
    clearError: () => setError(null),
  };
}
