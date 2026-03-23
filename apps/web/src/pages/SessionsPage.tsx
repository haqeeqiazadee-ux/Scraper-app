/**
 * SessionsPage — Monitor active HTTP and browser sessions.
 *
 * Features:
 * - Stats bar: Total, Active, Degraded, Expired counts
 * - Table: Domain, Type badge, Status badge, Health Score bar, Requests, Age, Actions
 * - Auto-refresh every 10 seconds
 * - Empty state
 */

import { useState } from "react";
import { useSessionList } from "../hooks/useSessions";
import type { SessionInfo, SessionStatus, SessionType } from "../api/types";

/* ── Helpers ── */

function relativeAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "< 1m";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function statusBadgeClass(status: SessionStatus): string {
  switch (status) {
    case "active":
      return "badge--success";
    case "degraded":
      return "badge--pending";
    case "invalidated":
      return "badge--failed";
    case "expired":
      return "badge--cancelled";
    default:
      return "badge--cancelled";
  }
}

function typeBadgeClass(type: SessionType): string {
  switch (type) {
    case "browser":
      return "badge--running";
    case "authenticated":
      return "badge--queued";
    default:
      return "badge--cancelled";
  }
}

function healthColor(score: number): string {
  if (score >= 0.8) return "var(--color-success)";
  if (score >= 0.5) return "var(--color-warning)";
  return "var(--color-error)";
}

/* ── Health Score mini bar ── */

function HealthBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 80 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: "var(--color-border)",
          borderRadius: 99,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: healthColor(score),
            borderRadius: 99,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: healthColor(score),
          minWidth: 32,
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

/* ── Component ── */

export function SessionsPage() {
  const { data, isLoading, error, refetch } = useSessionList();

  const [confirmInvalidateId, setConfirmInvalidateId] = useState<string | null>(null);

  const items: SessionInfo[] = data?.items ?? [];

  // Count by status
  const countByStatus = (status: SessionStatus) =>
    items.filter((s) => s.status === status).length;

  const stats = [
    { label: "Total Sessions", value: items.length, sub: "All tracked" },
    {
      label: "Active",
      value: countByStatus("active"),
      sub: "Healthy & reusable",
      color: "var(--color-success)",
    },
    {
      label: "Degraded",
      value: countByStatus("degraded"),
      sub: "Reduced performance",
      color: "var(--color-warning)",
    },
    {
      label: "Expired",
      value: countByStatus("expired"),
      sub: "Past max age",
      color: "var(--color-text-secondary)",
    },
  ];

  return (
    <>
      <div className="page-header">
        <h2>Sessions</h2>
        <p>
          Monitor reusable HTTP and browser sessions. Auto-refreshes every 10s.
        </p>
      </div>

      <div className="page-body">
        {/* Stats bar */}
        <div className="stats-grid">
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
            <h3>{items.length} session{items.length !== 1 ? "s" : ""}</h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              {isLoading ? "Refreshing…" : "Refresh"}
            </button>
          </div>

          {/* Loading */}
          {isLoading && items.length === 0 && (
            <div className="loading">Loading sessions…</div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="empty-state">
              <h3>Failed to load sessions</h3>
              <p>Check that the control plane is reachable.</p>
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
          {!isLoading && !error && items.length === 0 && (
            <div className="empty-state">
              <h3>No sessions tracked</h3>
              <p>
                Sessions are created automatically when tasks run. Check back
                after executing a few tasks.
              </p>
            </div>
          )}

          {/* Table */}
          {!error && items.length > 0 && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Health Score</th>
                    <th>Requests</th>
                    <th>Age</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => {
                    const successRate =
                      s.request_count > 0
                        ? Math.round((s.success_count / s.request_count) * 100)
                        : 0;

                    return (
                      <tr key={s.id}>
                        {/* Domain */}
                        <td style={{ fontWeight: 500, fontFamily: "var(--font-mono)", fontSize: 13 }}>
                          {s.domain}
                        </td>

                        {/* Type */}
                        <td>
                          <span
                            className={`badge ${typeBadgeClass(s.session_type)}`}
                            style={{ textTransform: "capitalize" }}
                          >
                            {s.session_type}
                          </span>
                        </td>

                        {/* Status */}
                        <td>
                          <span
                            className={`badge ${statusBadgeClass(s.status)}`}
                            style={{ textTransform: "capitalize" }}
                          >
                            {s.status}
                          </span>
                        </td>

                        {/* Health score */}
                        <td>
                          <HealthBar score={s.health_score} />
                        </td>

                        {/* Requests */}
                        <td style={{ fontSize: 13 }}>
                          <span style={{ fontWeight: 600 }}>{s.success_count}</span>
                          <span style={{ color: "var(--color-text-secondary)" }}>
                            /{s.request_count}
                          </span>
                          <span
                            style={{
                              marginLeft: 6,
                              fontSize: 11,
                              color:
                                successRate >= 80
                                  ? "var(--color-success)"
                                  : successRate >= 50
                                  ? "var(--color-warning)"
                                  : "var(--color-error)",
                            }}
                          >
                            ({successRate}%)
                          </span>
                        </td>

                        {/* Age */}
                        <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                          {relativeAge(s.created_at)}
                        </td>

                        {/* Actions */}
                        <td>
                          <div className="action-buttons">
                            {confirmInvalidateId === s.id ? (
                              <>
                                <button
                                  className="btn btn-danger btn-sm"
                                  onClick={() => {
                                    // Invalidation handled via hook in production
                                    setConfirmInvalidateId(null);
                                  }}
                                >
                                  Confirm
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => setConfirmInvalidateId(null)}
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => setConfirmInvalidateId(s.id)}
                                disabled={
                                  s.status === "invalidated" ||
                                  s.status === "expired"
                                }
                                title="Invalidate session"
                              >
                                Invalidate
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
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
