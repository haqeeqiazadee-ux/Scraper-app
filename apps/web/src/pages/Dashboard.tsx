/**
 * Dashboard page — overview of tasks with status counts, health indicator,
 * and quick actions. Polls task list every 10 seconds for real-time updates.
 */

import { useQuery } from "@tanstack/react-query";
import { tasks, health } from "../api/client";
import { TaskTable } from "../components/TaskTable";
import type { TaskListItem } from "../api/types";

function countByStatus(items: TaskListItem[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const item of items) {
    counts[item.status] = (counts[item.status] ?? 0) + 1;
  }
  return counts;
}

export function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["tasks", "dashboard"],
    queryFn: () => tasks.list({ limit: 20 }),
    refetchInterval: 10_000,
  });

  const { data: healthData } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
    refetchInterval: 30_000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const counts = countByStatus(items);

  const stats: { label: string; value: number | string; sub: string; color?: string }[] = [
    { label: "Total Tasks", value: total, sub: "Across all statuses" },
    {
      label: "Running",
      value: counts["running"] ?? 0,
      sub: "Currently executing",
      color: "var(--color-info)",
    },
    {
      label: "Completed",
      value: counts["completed"] ?? 0,
      sub: "Successfully finished",
      color: "var(--color-success)",
    },
    {
      label: "Failed",
      value: counts["failed"] ?? 0,
      sub: "Need attention",
      color: counts["failed"] ? "var(--color-error)" : undefined,
    },
  ];

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Dashboard</h2>
          <p>
            Overview of your scraping tasks and platform activity.
          </p>
        </div>
        {healthData && (
          <div className="page-header-actions">
            <span
              className={`badge badge--${healthData.status === "healthy" ? "success" : "warning"}`}
              style={{ fontSize: 12 }}
            >
              <span
                className={`status-dot status-dot--${healthData.status === "healthy" ? "success" : "warning"}`}
              />
              API {healthData.status}
            </span>
          </div>
        )}
      </div>
      <div className="page-body">
        {/* Stat cards */}
        <div className="stats-grid">
          {stats.map((s) => (
            <div key={s.label} className="stat-card" style={{ position: "relative", overflow: "hidden" }}>
              {s.color && (
                <div style={{
                  position: "absolute", top: 0, left: 0, right: 0, height: 2,
                  background: s.color, opacity: 0.5,
                }} />
              )}
              <div className="stat-label">{s.label}</div>
              <div className="stat-value" style={s.color ? { color: s.color } : {}}>
                {s.value}
              </div>
              <div className="stat-sub">{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Recent tasks */}
        <div className="card">
          <div className="card-header">
            <h3>Recent Tasks</h3>
            {total > 0 && (
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                Showing {items.length} of {total}
              </span>
            )}
          </div>
          {isLoading && <div className="loading">Loading tasks...</div>}
          {error && (
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <h3>Connection Error</h3>
              <p>Failed to load tasks. Is the control plane running?</p>
            </div>
          )}
          {!isLoading && !error && items.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <line x1="12" y1="8" x2="12" y2="16" />
                  <line x1="8" y1="12" x2="16" y2="12" />
                </svg>
              </div>
              <h3>No Tasks Yet</h3>
              <p>Create your first scraping task to get started.</p>
              <div className="empty-state-action">
                <a href="/tasks" className="btn btn-primary">Go to Tasks</a>
              </div>
            </div>
          )}
          {!isLoading && !error && items.length > 0 && <TaskTable tasks={items} />}
        </div>
      </div>
    </>
  );
}
