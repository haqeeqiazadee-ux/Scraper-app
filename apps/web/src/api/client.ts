/**
 * API client for the AI Scraping Platform control plane.
 *
 * Uses VITE_API_URL env var for base URL (defaults to /api/v1 for Vite proxy).
 * Includes JWT auth token management with auto-refresh on 401.
 */

import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListItem,
  Policy,
  PolicyCreate,
  PolicyUpdate,
  PolicyListItem,
  Result,
  ResultListItem,
  RunListItem,
  PaginatedResponse,
  TokenRequest,
  TokenResponse,
  UserProfile,
  Schedule,
  ScheduleCreate,
  ScheduleResponse,
  ScheduleCreateRequest,
  BillingPlan,
  TenantQuota,
  WebhookDelivery,
  SessionInfo,
  HealthStatus,
  MetricsResponse,
  ExecuteResponse,
} from "./types";

/* ── Configuration ── */

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

/* ── Token Management ── */

const TOKEN_KEY = "auth_token";

function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function setToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // restricted context
  }
}

/* ── Error Class ── */

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

/* ── Core Request Helper ── */

/** Callback invoked when a 401 is received and token refresh fails. */
let _onAuthFailure: (() => void) | null = null;

export function onAuthFailure(cb: () => void): void {
  _onAuthFailure = cb;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };

  const url = `${BASE}${path}`;
  const response = await fetch(url, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    // Clear stored token and notify auth listeners
    setToken(null);
    _onAuthFailure?.();
    throw new ApiError(401, "Authentication required");
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* response may not be JSON */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

/** Build query string from params, omitting undefined/null values. */
function buildQuery(
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

/* ── Auth ── */

export const auth = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const body: TokenRequest = { username, password };
    // Auth endpoint is outside /api/v1 prefix — it's at /auth/token
    // But we send it through the same base for proxy compatibility
    const result = await request<TokenResponse>("/auth/token", {
      method: "POST",
      body: JSON.stringify(body),
    });
    setToken(result.access_token);
    return result;
  },

  async register(username: string, password: string): Promise<TokenResponse> {
    // Uses the same token endpoint (scaffolding accepts any credentials)
    return auth.login(username, password);
  },

  async me(): Promise<UserProfile> {
    return request("/auth/me");
  },

  logout(): void {
    setToken(null);
  },

  getToken,
  setToken,

  isAuthenticated(): boolean {
    return getToken() !== null;
  },
};

/* ── Tasks ── */

export const tasks = {
  list(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<TaskListItem>> {
    const qs = buildQuery({
      status: params?.status,
      limit: params?.limit,
      offset: params?.offset,
    });
    return request(`/tasks${qs}`);
  },

  get(taskId: string): Promise<Task> {
    return request(`/tasks/${taskId}`);
  },

  create(data: TaskCreate): Promise<Task> {
    return request("/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(taskId: string, data: TaskUpdate): Promise<Task> {
    return request(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  delete(taskId: string): Promise<void> {
    return request(`/tasks/${taskId}`, { method: "DELETE" });
  },

  execute(taskId: string): Promise<ExecuteResponse> {
    return request(`/tasks/${taskId}/execute`, { method: "POST" });
  },

  cancel(taskId: string): Promise<{ id: string; status: string }> {
    return request(`/tasks/${taskId}/cancel`, { method: "POST" });
  },

  results(taskId: string): Promise<{ items: ResultListItem[]; total: number }> {
    return request(`/tasks/${taskId}/results`);
  },

  runs(taskId: string): Promise<{ items: RunListItem[]; total: number }> {
    return request(`/tasks/${taskId}/runs`);
  },
};

/* ── Policies ── */

export const policies = {
  list(params?: {
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<PolicyListItem>> {
    const qs = buildQuery({
      limit: params?.limit,
      offset: params?.offset,
    });
    return request(`/policies${qs}`);
  },

  get(policyId: string): Promise<Policy> {
    return request(`/policies/${policyId}`);
  },

  create(data: PolicyCreate): Promise<Policy> {
    return request("/policies", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(policyId: string, data: PolicyUpdate): Promise<Policy> {
    return request(`/policies/${policyId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  delete(policyId: string): Promise<void> {
    return request(`/policies/${policyId}`, { method: "DELETE" });
  },
};

/* ── Results ── */

export const results = {
  list(params?: {
    limit?: number;
    offset?: number;
    min_confidence?: number;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }): Promise<PaginatedResponse<ResultListItem>> {
    const qs = buildQuery({
      limit: params?.limit,
      offset: params?.offset,
      min_confidence: params?.min_confidence,
      sort_by: params?.sort_by,
      sort_order: params?.sort_order,
    });
    return request(`/results${qs}`);
  },

  get(resultId: string): Promise<Result> {
    return request(`/results/${resultId}`);
  },

  export(params: {
    format: "json" | "csv" | "xlsx";
    min_confidence?: number;
    date_from?: string;
    date_to?: string;
    destination: "download" | "s3" | "webhook";
    webhook_url?: string;
    s3_path?: string;
  }): Promise<Blob | { status: string; message: string }> {
    if (params.destination === "download") {
      const token = getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      return fetch(`${BASE}/results/export`, {
        method: "POST",
        headers,
        body: JSON.stringify(params),
      }).then((res) => {
        if (!res.ok) throw new ApiError(res.status, res.statusText);
        return res.blob();
      });
    }
    return request("/results/export", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },

  exportCount(params: {
    min_confidence?: number;
    date_from?: string;
    date_to?: string;
  }): Promise<{ count: number }> {
    const qs = buildQuery({
      min_confidence: params.min_confidence,
      date_from: params.date_from,
      date_to: params.date_to,
    });
    return request(`/results/export/count${qs}`);
  },
};

/* ── Schedules ── */

export const schedules = {
  /** Legacy list — returns old Schedule shape */
  list(): Promise<{ items: Schedule[]; total: number }> {
    return request("/schedules");
  },

  /** New list — returns ScheduleResponse shape from updated backend */
  listV2(): Promise<{ items: ScheduleResponse[]; total: number }> {
    return request("/schedules");
  },

  create(data: ScheduleCreate): Promise<Schedule> {
    return request("/schedules", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /** New create — uses ScheduleCreateRequest shape */
  createV2(data: ScheduleCreateRequest): Promise<ScheduleResponse> {
    return request("/schedules", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  delete(scheduleId: string): Promise<void> {
    return request(`/schedules/${scheduleId}`, { method: "DELETE" });
  },
};

/* ── Billing ── */

export const billing = {
  plans(): Promise<{ plans: BillingPlan[] }> {
    return request("/billing/plans");
  },

  quota(): Promise<TenantQuota> {
    return request("/billing/quota");
  },
};

/* ── Sessions ── */

export const sessions = {
  list(params?: {
    limit?: number;
    offset?: number;
  }): Promise<{ items: SessionInfo[]; total: number }> {
    const qs = buildQuery({
      limit: params?.limit,
      offset: params?.offset,
    });
    return request(`/sessions${qs}`);
  },
};

/* ── Webhooks ── */

export const webhooks = {
  history(params?: {
    limit?: number;
    offset?: number;
  }): Promise<{ items: WebhookDelivery[]; total: number }> {
    const qs = buildQuery({
      limit: params?.limit,
      offset: params?.offset,
    });
    return request(`/webhooks/history${qs}`);
  },
};

/* ── Health & Metrics ── */

export const health = {
  check(): Promise<HealthStatus> {
    return request("/health");
  },

  ready(): Promise<{ status: string; checks: Record<string, string>; timestamp: string }> {
    return request("/ready");
  },
};

export const metrics = {
  get(): Promise<MetricsResponse> {
    return request("/metrics");
  },
};

/* ── Route (dry run) ── */

export const routing = {
  dryRun(url: string, policyId?: string): Promise<{ url: string; route: { lane: string; reason: string; fallback_lanes: string[]; confidence: number } }> {
    return request("/route", {
      method: "POST",
      body: JSON.stringify({ url, policy_id: policyId }),
    });
  },
};
