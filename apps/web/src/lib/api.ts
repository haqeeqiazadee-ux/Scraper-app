/**
 * API client helper with base URL config, auth header injection, and error handling.
 *
 * This wraps the lower-level client from ../api/client.ts with additional
 * utilities for token management and request configuration.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Stored auth token (in-memory; persisted to sessionStorage). */
let _authToken: string | null = null;

export function getAuthToken(): string | null {
  if (_authToken) return _authToken;
  try {
    _authToken = sessionStorage.getItem("auth_token");
  } catch {
    // SSR or restricted context
  }
  return _authToken;
}

export function setAuthToken(token: string | null): void {
  _authToken = token;
  try {
    if (token) {
      sessionStorage.setItem("auth_token", token);
    } else {
      sessionStorage.removeItem("auth_token");
    }
  } catch {
    // SSR or restricted context
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

/**
 * Core request helper. Handles:
 * - Base URL resolution
 * - Auth header injection
 * - JSON content-type
 * - Error parsing
 */
export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };

  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response may not be JSON
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
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
