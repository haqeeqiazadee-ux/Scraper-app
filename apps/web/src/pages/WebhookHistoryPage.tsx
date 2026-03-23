/**
 * WebhookHistoryPage — Audit log of all webhook delivery attempts.
 *
 * Features:
 * - Stats: Total Deliveries, Success Rate, Avg Attempts
 * - Table: Task ID (linked), Callback URL (truncated), Status badge,
 *   HTTP Status Code, Attempts, HMAC validity badge, Delivered At (relative)
 * - Expandable row showing full payload JSON
 * - Empty state
 * - Auto-refresh every 30s
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { WebhookDelivery } from "../api/types";

/* ── Helpers ── */

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function truncateUrl(url: string, max = 48): string {
  if (url.length <= max) return url;
  return url.slice(0, max) + "…";
}

function truncateId(id: string): string {
  return id.length > 12 ? id.slice(0, 8) + "…" : id;
}

function httpStatusColor(code: number | null): string {
  if (code === null) return "var(--color-text-secondary)";
  if (code >= 200 && code < 300) return "var(--color-success)";
  if (code >= 400 && code < 500) return "var(--color-warning)";
  return "var(--color-error)";
}

/* ── Skeleton row ── */

function SkeletonRow() {
  return (
    <tr>
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i}>
          <div
            style={{
              height: 14,
              background: "var(--color-border)",
              borderRadius: 4,
              opacity: 0.5,
              width: i === 0 ? 90 : i === 1 ? 180 : 70,
            }}
          />
        </td>
      ))}
    </tr>
  );
}

/* ── Data hook stub ── */
// The real useWebhookHistory hook will come from the parallel agent.
// This stub compiles independently and wires to the correct endpoint.

interface WebhookHistoryPage {
  items: (WebhookDelivery & { hmac_valid?: boolean; payload?: unknown })[];
  total: number;
}

function useWebhookHistory(options?: { refetchInterval?: number }) {
  return useQuery<WebhookHistoryPage>({
    queryKey: ["webhooks", "history"],
    queryFn: async () => {
      const res = await fetch("/api/v1/webhooks/history?limit=100");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<WebhookHistoryPage>;
    },
    refetchInterval: options?.refetchInterval,
  });
}

/* ── Component ── */

export function WebhookHistoryPage() {
  const { data, isLoading, error, refetch } = useWebhookHistory({
    refetchInterval: 30_000,
  });

  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const deliveries = data?.items ?? [];
  const total = data?.total ?? deliveries.length;

  // Aggregate stats
  const successCount = deliveries.filter((d) => d.success).length;
  const successRate =
    total > 0 ? Math.round((successCount / total) * 100) : 0;
  const avgAttempts =
    deliveries.length > 0
      ? (
          deliveries.reduce((s, d) => s + d.attempts, 0) / deliveries.length
        ).toFixed(1)
      : "—";

  const stats = [
    { label: "Total Deliveries", value: total, sub: "All time" },
    {
      label: "Success Rate",
      value: total > 0 ? `${successRate}%` : "—",
      sub: `${successCount} successful`,
      color:
        successRate >= 95
          ? "var(--color-success)"
          : successRate >= 80
          ? "var(--color-warning)"
          : total > 0
          ? "var(--color-error)"
          : undefined,
    },
    {
      label: "Avg Attempts",
      value: avgAttempts,
      sub: "Per delivery",
    },
  ];

  function toggleRow(key: string) {
    setExpandedRow((prev) => (prev === key ? null : key));
  }

  return (
    <>
      <div className="page-header">
        <h2>Webhook History</h2>
        <p>
          Delivery audit log for task callback webhooks. Auto-refreshes every
          30s.
        </p>
      </div>

      <div className="page-body">
        {/* Stats */}
        <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          {stats.map((s) => (
            <div key={s.label} className="stat-card">
              <div className="stat-label">{s.label}</div>
              <div
                className="stat-value"
                style={s.color ? { color: s.color } : undefined}
              >
                {s.value}
              </div>
              <div className="stat-sub">{s.sub}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>
              {total} deliver{total !== 1 ? "ies" : "y"}
            </h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              {isLoading ? "Refreshing…" : "Refresh"}
            </button>
          </div>

          {/* Error */}
          {error && !isLoading && (
            <div className="empty-state">
              <h3>Failed to load webhook history</h3>
              <p>Check the control plane connection and try again.</p>
              <button
                className="btn btn-secondary"
                style={{ marginTop: 16 }}
                onClick={() => refetch()}
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty */}
          {!isLoading && !error && deliveries.length === 0 && (
            <div className="empty-state">
              <h3>No webhook deliveries yet</h3>
              <p>
                Webhook deliveries appear here once tasks with a{" "}
                <code
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    background: "var(--color-bg)",
                    padding: "1px 5px",
                    borderRadius: 3,
                    border: "1px solid var(--color-border)",
                  }}
                >
                  callback_url
                </code>{" "}
                complete. Each delivery is signed with HMAC-SHA256.
              </p>
            </div>
          )}

          {/* Table */}
          {!error && (isLoading || deliveries.length > 0) && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Task ID</th>
                    <th>Callback URL</th>
                    <th>Status</th>
                    <th>HTTP Code</th>
                    <th>Attempts</th>
                    <th>HMAC</th>
                    <th>Delivered</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading && deliveries.length === 0
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <SkeletonRow key={i} />
                      ))
                    : deliveries.map((d, idx) => {
                        const rowKey = `${d.task_id}-${idx}`;
                        const isExpanded = expandedRow === rowKey;
                        const hasPayload = !!d.payload;

                        return (
                          <>
                            <tr
                              key={rowKey}
                              style={{
                                cursor: hasPayload ? "pointer" : undefined,
                              }}
                              onClick={
                                hasPayload
                                  ? () => toggleRow(rowKey)
                                  : undefined
                              }
                              title={
                                hasPayload ? "Click to view payload" : undefined
                              }
                            >
                              {/* Task ID */}
                              <td>
                                <a
                                  href={`/tasks/${d.task_id}`}
                                  onClick={(e) => e.stopPropagation()}
                                  style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 12,
                                    color: "var(--color-primary)",
                                  }}
                                  title={d.task_id}
                                >
                                  {truncateId(d.task_id)}
                                </a>
                              </td>

                              {/* Callback URL */}
                              <td>
                                <span
                                  title={d.callback_url}
                                  style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 12,
                                    color: "var(--color-text-secondary)",
                                  }}
                                >
                                  {truncateUrl(d.callback_url)}
                                </span>
                              </td>

                              {/* Status badge */}
                              <td>
                                <span
                                  className={`badge ${
                                    d.success
                                      ? "badge--completed"
                                      : "badge--failed"
                                  }`}
                                >
                                  {d.success ? "Success" : "Failed"}
                                </span>
                              </td>

                              {/* HTTP status code */}
                              <td>
                                {d.status_code !== null ? (
                                  <span
                                    style={{
                                      fontFamily: "var(--font-mono)",
                                      fontSize: 13,
                                      fontWeight: 600,
                                      color: httpStatusColor(d.status_code),
                                    }}
                                  >
                                    {d.status_code}
                                  </span>
                                ) : (
                                  <span
                                    style={{
                                      color: "var(--color-text-secondary)",
                                      fontSize: 13,
                                    }}
                                  >
                                    —
                                  </span>
                                )}
                              </td>

                              {/* Attempts */}
                              <td
                                style={{
                                  fontSize: 13,
                                  color:
                                    d.attempts > 1
                                      ? "var(--color-warning)"
                                      : "var(--color-text-secondary)",
                                  fontWeight: d.attempts > 1 ? 600 : undefined,
                                }}
                              >
                                {d.attempts}
                              </td>

                              {/* HMAC status */}
                              <td>
                                {"hmac_valid" in d ? (
                                  <span
                                    className={`badge ${
                                      (d as { hmac_valid?: boolean }).hmac_valid
                                        ? "badge--completed"
                                        : "badge--failed"
                                    }`}
                                  >
                                    {(d as { hmac_valid?: boolean }).hmac_valid
                                      ? "Valid"
                                      : "Invalid"}
                                  </span>
                                ) : (
                                  <span
                                    style={{
                                      color: "var(--color-text-secondary)",
                                      fontSize: 12,
                                    }}
                                  >
                                    —
                                  </span>
                                )}
                              </td>

                              {/* Delivered At */}
                              <td
                                style={{
                                  fontSize: 13,
                                  color: "var(--color-text-secondary)",
                                }}
                              >
                                {relativeTime(d.delivered_at)}
                              </td>
                            </tr>

                            {/* Expandable payload row */}
                            {isExpanded && hasPayload && (
                              <tr key={`${rowKey}-payload`}>
                                <td
                                  colSpan={7}
                                  style={{
                                    background: "var(--color-bg)",
                                    padding: "0 12px 16px",
                                  }}
                                >
                                  <div
                                    style={{
                                      marginTop: 8,
                                      borderRadius: "var(--radius-md)",
                                      border: "1px solid var(--color-border)",
                                      overflow: "hidden",
                                    }}
                                  >
                                    <div
                                      style={{
                                        padding: "8px 12px",
                                        background: "#1e293b",
                                        borderBottom:
                                          "1px solid rgba(255,255,255,0.06)",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "space-between",
                                      }}
                                    >
                                      <span
                                        style={{
                                          fontSize: 11,
                                          fontWeight: 600,
                                          color: "#94a3b8",
                                          textTransform: "uppercase",
                                          letterSpacing: "0.06em",
                                        }}
                                      >
                                        Payload JSON
                                      </span>
                                      <button
                                        className="btn btn-sm"
                                        style={{
                                          background: "transparent",
                                          border: "none",
                                          color: "#64748b",
                                          padding: "2px 6px",
                                          fontSize: 12,
                                        }}
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          toggleRow(rowKey);
                                        }}
                                      >
                                        ✕
                                      </button>
                                    </div>
                                    <pre
                                      style={{
                                        margin: 0,
                                        padding: "12px 16px",
                                        background: "#0f172a",
                                        color: "#e2e8f0",
                                        fontFamily: "var(--font-mono)",
                                        fontSize: 12,
                                        lineHeight: 1.6,
                                        overflowX: "auto",
                                        maxHeight: 320,
                                        overflowY: "auto",
                                      }}
                                    >
                                      {JSON.stringify(d.payload, null, 2)}
                                    </pre>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
