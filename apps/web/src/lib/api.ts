/**
 * API client helper — DEPRECATED.
 *
 * This module is kept for backward compatibility. New code should import
 * directly from "../api/client" which handles auth token management,
 * 401 auto-logout, and all API endpoints.
 *
 * Re-exports the key utilities from the canonical client.
 */

export { ApiError } from "../api/client";
import { auth } from "../api/client";

/** @deprecated Use `auth.getToken()` from "../api/client" */
export function getAuthToken(): string | null {
  return auth.getToken();
}

/** @deprecated Use `auth.setToken(token)` from "../api/client" */
export function setAuthToken(token: string | null): void {
  auth.setToken(token);
}

/** Build query string from params, omitting undefined/null values. */
export function buildQuery(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== "") {
      query.set(key, String(value));
    }
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}
