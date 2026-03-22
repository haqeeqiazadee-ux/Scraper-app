/**
 * AI Scraper — Cloud API Client
 *
 * Communicates with the cloud control plane for task management,
 * extraction execution, and result retrieval. Handles auth token
 * refresh and offline detection.
 *
 * Base URL is configurable via chrome.storage.local ("apiEndpoint").
 * Auth uses Bearer tokens stored in chrome.storage.local ("authToken").
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiClientConfig {
  baseUrl: string;
  apiKey: string;
  authToken?: string;
  tokenExpiry?: number;
}

export interface TaskConfig {
  url: string;
  mode: string;
  selectors?: SelectorConfig[];
  policy_id?: string;
  priority?: number;
  metadata?: Record<string, unknown>;
}

export interface SelectorConfig {
  name: string;
  selector: string;
  type: "css" | "xpath";
  multiple?: boolean;
}

export interface TaskResult {
  id: string;
  task_id: string;
  data: Record<string, unknown>;
  confidence: number;
  extraction_method: string;
  source: string;
  timestamp: string;
}

export interface TaskStatus {
  id: string;
  status: string;
  progress?: number;
  message?: string;
  created_at: string;
  updated_at: string;
}

export interface CloudStatus {
  connected: boolean;
  healthy: boolean;
  latency_ms: number;
  version?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

async function getStoredConfig(): Promise<ApiClientConfig> {
  const defaults: ApiClientConfig = {
    baseUrl: "http://localhost:8000",
    apiKey: "",
    authToken: undefined,
    tokenExpiry: 0,
  };
  const stored = await chrome.storage.local.get([
    "apiEndpoint",
    "apiKey",
    "authToken",
    "tokenExpiry",
  ]);
  return {
    baseUrl: (stored.apiEndpoint as string) || defaults.baseUrl,
    apiKey: (stored.apiKey as string) || defaults.apiKey,
    authToken: stored.authToken as string | undefined,
    tokenExpiry: (stored.tokenExpiry as number) || 0,
  };
}

async function storeAuthToken(token: string, expiresIn: number): Promise<void> {
  const expiry = Date.now() + expiresIn * 1000;
  await chrome.storage.local.set({
    authToken: token,
    tokenExpiry: expiry,
  });
}

function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

function isTokenExpired(expiry: number | undefined): boolean {
  if (!expiry) return true;
  // Consider expired if less than 60 seconds remain
  return Date.now() > expiry - 60_000;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

async function apiFetch(
  path: string,
  options: RequestInit = {},
  config?: ApiClientConfig
): Promise<Response> {
  const cfg = config || (await getStoredConfig());
  const url = `${normalizeBaseUrl(cfg.baseUrl)}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Attach auth token if available and not expired
  if (cfg.authToken && !isTokenExpired(cfg.tokenExpiry)) {
    headers["Authorization"] = `Bearer ${cfg.authToken}`;
  } else if (cfg.apiKey) {
    headers["Authorization"] = `Bearer ${cfg.apiKey}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // If 401 and we have an API key, try to refresh the token
  if (response.status === 401 && cfg.apiKey) {
    const refreshed = await refreshToken(cfg);
    if (refreshed) {
      headers["Authorization"] = `Bearer ${refreshed}`;
      return fetch(url, { ...options, headers });
    }
  }

  return response;
}

async function refreshToken(cfg: ApiClientConfig): Promise<string | null> {
  try {
    const url = `${normalizeBaseUrl(cfg.baseUrl)}/api/v1/auth/token`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: cfg.apiKey,
        grant_type: "api_key",
      }),
    });

    if (!response.ok) return null;

    const data = (await response.json()) as AuthResponse;
    await storeAuthToken(data.access_token, data.expires_in);
    return data.access_token;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Public API methods
// ---------------------------------------------------------------------------

/**
 * Authenticate with the cloud control plane using an API key.
 * Stores the resulting auth token in chrome.storage.local.
 */
export async function login(apiKey: string): Promise<boolean> {
  const cfg = await getStoredConfig();
  cfg.apiKey = apiKey;

  try {
    const url = `${normalizeBaseUrl(cfg.baseUrl)}/api/v1/auth/token`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: apiKey,
        grant_type: "api_key",
      }),
    });

    if (!response.ok) return false;

    const data = (await response.json()) as AuthResponse;
    await storeAuthToken(data.access_token, data.expires_in);
    await chrome.storage.local.set({ apiKey });
    return true;
  } catch {
    return false;
  }
}

/**
 * Create a new extraction task on the cloud control plane.
 */
export async function createTask(config: TaskConfig): Promise<TaskStatus> {
  const response = await apiFetch("/api/v1/tasks", {
    method: "POST",
    body: JSON.stringify({
      url: config.url,
      task_type: config.mode || "auto",
      priority: config.priority ?? 5,
      config: {
        selectors: config.selectors,
        policy_id: config.policy_id,
        metadata: config.metadata,
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to create task (${response.status}): ${text}`);
  }

  return response.json() as Promise<TaskStatus>;
}

/**
 * Execute a previously created task.
 */
export async function executeTask(taskId: string): Promise<TaskStatus> {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/execute`, {
    method: "POST",
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to execute task (${response.status}): ${text}`);
  }

  return response.json() as Promise<TaskStatus>;
}

/**
 * Get results for a completed task.
 */
export async function getResults(taskId: string): Promise<TaskResult[]> {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/results`);

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to get results (${response.status}): ${text}`);
  }

  return response.json() as Promise<TaskResult[]>;
}

/**
 * Check cloud control plane connectivity and health.
 */
export async function getStatus(): Promise<CloudStatus> {
  const start = Date.now();
  try {
    const cfg = await getStoredConfig();
    const url = `${normalizeBaseUrl(cfg.baseUrl)}/health`;
    const response = await fetch(url, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    });

    const latency = Date.now() - start;

    if (!response.ok) {
      return { connected: true, healthy: false, latency_ms: latency };
    }

    const data = (await response.json()) as { version?: string };
    return {
      connected: true,
      healthy: true,
      latency_ms: latency,
      version: data.version,
    };
  } catch {
    return {
      connected: false,
      healthy: false,
      latency_ms: Date.now() - start,
    };
  }
}

/**
 * Get the status of a specific task.
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await apiFetch(`/api/v1/tasks/${taskId}`);

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to get task status (${response.status}): ${text}`);
  }

  return response.json() as Promise<TaskStatus>;
}

/**
 * Send raw extraction data to the cloud for AI normalization.
 */
export async function sendForNormalization(payload: {
  url: string;
  mode: string;
  raw: Record<string, unknown>;
}): Promise<Record<string, unknown>> {
  const response = await apiFetch("/api/v1/extract", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Normalization failed (${response.status}): ${text}`);
  }

  return response.json() as Promise<Record<string, unknown>>;
}
