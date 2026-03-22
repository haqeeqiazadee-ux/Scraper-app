/**
 * API client for the AI Scraping Platform control plane.
 *
 * All endpoints are prefixed with /api/v1 and proxied via Vite dev server.
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
  PaginatedResponse,
} from "./types";

const BASE = "/api/v1";

/* ── Helpers ── */

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

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

/* ── Tasks ── */

export const tasks = {
  list(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<TaskListItem>> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit != null) query.set("limit", String(params.limit));
    if (params?.offset != null) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request(`/tasks${qs ? `?${qs}` : ""}`);
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

  cancel(taskId: string): Promise<{ id: string; status: string }> {
    return request(`/tasks/${taskId}/cancel`, { method: "POST" });
  },

  results(taskId: string): Promise<{ items: ResultListItem[]; total: number }> {
    return request(`/tasks/${taskId}/results`);
  },
};

/* ── Policies ── */

export const policies = {
  list(params?: {
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<PolicyListItem>> {
    const query = new URLSearchParams();
    if (params?.limit != null) query.set("limit", String(params.limit));
    if (params?.offset != null) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request(`/policies${qs ? `?${qs}` : ""}`);
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
  get(resultId: string): Promise<Result> {
    return request(`/results/${resultId}`);
  },
};

/* ── Health ── */

export const health = {
  check(): Promise<{ status: string }> {
    return request("/health");
  },
};

export { ApiError };
