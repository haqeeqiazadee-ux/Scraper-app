/**
 * Dashboard page — overview of tasks with status counts and health indicator.
 * Polls task list every 10 seconds for real-time status updates.
 */

import { useQuery } from "@tanstack/react-query";
import { tasks, health } from "../api/client";
import { TaskTable } from "../components/TaskTable";
import type { TaskListItem } from "../api/types";

/** Count items by status. */
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
    refetchInterval: 10_000, // Poll every 10 seconds for real-time updates
  });

  const { data: healthData } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
    refetchInterval: 30_000, // Check health every 30 seconds
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const counts = countByStatus(items);

  const stats: { label: string; value: number | string; sub: string }[] = [
    { label: "Total Tasks", value: total, sub: "Across all statuses" },
    {
      label: "Running",
      value: counts["running"] ?? 0,
      sub: "Currently executing",
    },
    {
      label: "Completed",
      value: counts["completed"] ?? 0,
      sub: "Successfully finished",
    },
    { label: "Failed", value: counts["failed"] ?? 0, sub: "Need attention" },
  ];

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>
          Overview of your scraping tasks and platform activity.
          {healthData && (
            <span
              style={{
                marginLeft: 12,
                fontSize: 12,
                fontWeight: 600,
                color:
                  healthData.status === "healthy"
                    ? "var(--color-success)"
                    : "var(--color-warning)",
              }}
            >
              API: {healthData.status}
            </span>
          )}
        </p>
      </div>
      <div className="page-body">
        <div className="stats-grid">
          {stats.map((s) => (
            <div key={s.label} className="stat-card">
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{s.value}</div>
              <div className="stat-sub">{s.sub}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Recent Tasks</h3>
          </div>
          {isLoading && <div className="loading">Loading tasks...</div>}
          {error && (
            <div className="empty-state">
              <p>Failed to load tasks. Is the control plane running?</p>
            </div>
          )}
          {!isLoading && !error && <TaskTable tasks={items} />}
        </div>
      </div>
    </>
  );
}
