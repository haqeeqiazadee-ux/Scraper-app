/**
 * TypeScript types matching the backend Pydantic contracts.
 * Keep in sync with packages/contracts/*.py
 */

/* ── Enums ── */

export type TaskStatus =
  | "pending"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type TaskType = "scrape" | "monitor" | "extract";

export type ExtractionType = "css" | "xpath" | "ai" | "auto";

export type LanePreference = "api" | "http" | "browser" | "hard_target" | "auto";

export type SessionStatus = "active" | "degraded" | "expired" | "invalidated";

export type SessionType = "http" | "browser" | "authenticated";

export type RunStatus = "running" | "success" | "failed" | "timeout" | "blocked";

export type ArtifactType =
  | "html_snapshot"
  | "screenshot"
  | "export_xlsx"
  | "export_json"
  | "export_csv";

export type PlanTier = "free" | "starter" | "pro" | "enterprise";

/* ── Task ── */

export interface Task {
  id: string;
  tenant_id: string;
  name: string;
  url: string;
  task_type: TaskType;
  extraction_type: ExtractionType;
  selectors: string[];
  policy_id: string | null;
  priority: number;
  schedule: string | null;
  callback_url: string | null;
  metadata: Record<string, unknown>;
  status: TaskStatus;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TaskCreate {
  name: string;
  url: string;
  task_type?: TaskType;
  extraction_type?: ExtractionType;
  selectors?: string[];
  policy_id?: string;
  priority?: number;
  schedule?: string;
  callback_url?: string;
  metadata?: Record<string, unknown>;
}

export interface TaskUpdate {
  name?: string;
  url?: string;
  extraction_type?: ExtractionType;
  selectors?: string[];
  status?: TaskStatus;
  policy_id?: string | null;
  priority?: number;
  schedule?: string | null;
  callback_url?: string;
  metadata?: Record<string, unknown>;
}

/** Shape returned by GET /api/v1/tasks (list items) */
export interface TaskListItem {
  id: string;
  name: string;
  url: string;
  task_type: TaskType;
  extraction_type: ExtractionType;
  priority: number;
  status: TaskStatus;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
}

/** Shape returned by GET /api/v1/tasks/{id}/runs */
export interface RunListItem {
  id: string;
  task_id: string;
  lane: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number;
  status: RunStatus;
  status_code: number | null;
  bytes_downloaded: number;
  records_found: number;
}

/* ── Policy ── */

export interface RateLimit {
  max_requests_per_minute: number;
  max_requests_per_hour: number;
  max_concurrent: number;
}

export interface ProxyPolicy {
  enabled: boolean;
  geo: string | null;
  proxy_type: string | null;
  rotation_strategy: string;
  sticky_session: boolean;
}

export interface SessionPolicy {
  reuse_sessions: boolean;
  max_session_age_minutes: number;
  max_requests_per_session: number;
  rotate_on_failure: boolean;
}

export interface RetryPolicy {
  max_retries: number;
  backoff_base_seconds: number;
  backoff_max_seconds: number;
  retry_on_status_codes: number[];
}

export interface Policy {
  id: string;
  tenant_id: string;
  name: string;
  target_domains: string[];
  preferred_lane: LanePreference;
  extraction_rules: Record<string, unknown>;
  rate_limit: RateLimit;
  proxy_policy: ProxyPolicy;
  session_policy: SessionPolicy;
  retry_policy: RetryPolicy;
  timeout_ms: number;
  robots_compliance: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface PolicyCreate {
  name: string;
  target_domains?: string[];
  preferred_lane?: LanePreference;
  extraction_rules?: Record<string, unknown>;
  rate_limit?: Partial<RateLimit>;
  proxy_policy?: Partial<ProxyPolicy>;
  session_policy?: Partial<SessionPolicy>;
  retry_policy?: Partial<RetryPolicy>;
  timeout_ms?: number;
  robots_compliance?: boolean;
}

export interface PolicyUpdate {
  name?: string;
  target_domains?: string[];
  preferred_lane?: LanePreference;
  extraction_rules?: Record<string, unknown>;
  rate_limit?: Partial<RateLimit>;
  proxy_policy?: Partial<ProxyPolicy>;
  session_policy?: Partial<SessionPolicy>;
  retry_policy?: Partial<RetryPolicy>;
  timeout_ms?: number;
  robots_compliance?: boolean;
}

export interface PolicyListItem {
  id: string;
  name: string;
  preferred_lane: LanePreference;
  target_domains: string[];
  timeout_ms: number;
  created_at: string;
}

/* ── Result ── */

export interface Result {
  id: string;
  task_id: string;
  run_id: string;
  tenant_id: string;
  url: string;
  extracted_data: Record<string, unknown>[];
  item_count: number;
  confidence: number;
  extraction_method: string;
  normalization_applied: boolean;
  dedup_applied: boolean;
  created_at: string;
  artifacts: string[];
}

export interface ResultListItem {
  id: string;
  run_id: string;
  url: string;
  item_count: number;
  confidence: number;
  extraction_method: string;
  created_at: string;
}

/* ── Run ── */

export interface Run {
  id: string;
  task_id: string;
  tenant_id: string;
  lane: string;
  connector: string;
  session_id: string | null;
  proxy_used: string | null;
  attempt: number;
  started_at: string;
  completed_at: string | null;
  duration_ms: number;
  status: RunStatus;
  status_code: number | null;
  error: string | null;
  bytes_downloaded: number;
  ai_tokens_used: number;
}

/* ── Artifact ── */

export interface Artifact {
  id: string;
  result_id: string;
  tenant_id: string;
  artifact_type: ArtifactType;
  storage_path: string;
  content_type: string;
  size_bytes: number;
  checksum: string;
  created_at: string;
  expires_at: string | null;
}

/* ── Billing ── */

export interface UsageCounters {
  tasks_today: number;
  browser_minutes_today: number;
  ai_tokens_today: number;
  storage_bytes_used: number;
  proxy_requests_today: number;
}

export interface TenantQuota {
  tenant_id: string;
  plan: PlanTier;
  max_tasks_per_day: number;
  max_concurrent_tasks: number;
  max_browser_minutes_per_day: number;
  max_ai_tokens_per_day: number;
  max_storage_bytes: number;
  max_proxy_requests_per_day: number;
  current_usage: UsageCounters;
  billing_cycle_start: string;
  billing_cycle_end: string;
}

/* ── Auth ── */

export interface TokenRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  sub: string;
  tenant_id: string;
  roles: string[];
}

/* ── Schedule ── */

export interface Schedule {
  id: string;
  task_id: string;
  cron: string;
  enabled: boolean;
  next_run: string | null;
  created_at: string;
}

export interface ScheduleCreate {
  task_id: string;
  cron: string;
  enabled?: boolean;
}

/* ── Health / Metrics ── */

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface MetricsResponse {
  [key: string]: unknown;
}

/* ── API Error ── */

export interface ApiErrorResponse {
  detail: string;
  status: number;
}

/* ── Route Decision ── */

export interface RouteDecision {
  lane: string;
  reason: string;
  fallback_lanes: string[];
  confidence: number;
}

export interface ExecuteResponse {
  task_id: string;
  status: string;
  route: RouteDecision;
}

/* ── Paginated responses ── */

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

/* ── Schedule (updated to match backend) ── */
export interface ScheduleResponse {
  schedule_id: string;
  task_id: string;
  schedule: string;
  schedule_type: "cron" | "interval" | "one_time";
  active: boolean;
  url: string;
  created_at: string;
  last_fired: string | null;
}

export interface ScheduleCreateRequest {
  url: string;
  schedule: string;
  task_type?: TaskType;
  priority?: number;
  callback_url?: string;
  webhook_secret?: string;
  metadata?: Record<string, unknown>;
}

/* ── Billing ── */
export interface BillingPlan {
  tier: PlanTier;
  price_cents: number;
  price_display: string;
}

/* ── Webhook ── */
export interface WebhookDelivery {
  task_id: string;
  callback_url: string;
  status_code: number | null;
  success: boolean;
  attempts: number;
  error: string | null;
  delivered_at: string;
}

/* ── Session ── */
export interface SessionInfo {
  id: string;
  domain: string;
  session_type: SessionType;
  status: SessionStatus;
  health_score: number;
  request_count: number;
  success_count: number;
  failure_count: number;
  created_at: string;
}

/* ── Proxy ── */
export interface ProxyInfo {
  host: string;
  port: number;
  protocol: string;
  geo: string | null;
  success_rate: number;
  avg_response_time: number;
  score: number;
  total_requests: number;
  is_available: boolean;
}

/* ── Analytics ── */
export interface AnalyticsData {
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  success_rate: number;
  avg_duration_ms: number;
  lane_distribution: Record<string, number>;
  top_domains: { domain: string; count: number }[];
  tasks_today: number;
}

/* ── Crawl (HYDRA) ── */

export interface CrawlStats {
  pages_crawled: number;
  pages_queued: number;
  pages_failed: number;
  items_extracted: number;
  bytes_downloaded: number;
  elapsed_seconds: number;
  pages_per_second: number;
  current_depth: number;
}

export interface CrawlJob {
  crawl_id: string;
  state: string;
  config: Record<string, any>;
  stats: CrawlStats;
  results: any[];
  errors: any[];
  created_at: string;
  updated_at: string;
}

/* ── Search (HYDRA) ── */

export interface SearchResult {
  query: string;
  results: Array<{
    url: string;
    title: string;
    extracted_data: Record<string, any>;
    status: string;
  }>;
  total_results: number;
  search_provider: string;
}

/* ── Extract (HYDRA) ── */

export interface ExtractResult {
  url: string;
  extracted_data: Record<string, any>;
  confidence: number;
  extraction_method: string;
}
