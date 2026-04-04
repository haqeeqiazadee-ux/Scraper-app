/**
 * Dashboard page — overview of tasks with status counts, health indicator,
 * quick actions, and recent task list. Polls task list every 10 seconds
 * for real-time updates.
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
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

function formatTime(date: Date): string {
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function Dashboard() {
  const navigate = useNavigate();
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const { data, isLoading, error, dataUpdatedAt } = useQuery({
    queryKey: ["tasks", "dashboard"],
    queryFn: () => tasks.list({ limit: 20 }),
    refetchInterval: 10_000,
  });

  const { data: healthData } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
    refetchInterval: 30_000,
  });

  // Track when data was last refreshed
  useEffect(() => {
    if (dataUpdatedAt) {
      setLastRefreshed(new Date(dataUpdatedAt));
    }
  }, [dataUpdatedAt]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const counts = countByStatus(items);

  const stats: {
    label: string;
    value: number | string;
    sub: string;
    variant: string;
  }[] = [
    {
      label: "Total Tasks",
      value: total,
      sub: "Across all statuses",
      variant: "stat-primary",
    },
    {
      label: "Running",
      value: counts["running"] ?? 0,
      sub: "Currently executing",
      variant: "stat-warning",
    },
    {
      label: "Completed",
      value: counts["completed"] ?? 0,
      sub: "Successfully finished",
      variant: "stat-success",
    },
    {
      label: "Failed",
      value: counts["failed"] ?? 0,
      sub: "Need attention",
      variant: counts["failed"] ? "stat-error" : "stat-primary",
    },
  ];

  const quickActions: {
    title: string;
    description: string;
    route: string;
    iconBg: string;
    icon: JSX.Element;
  }[] = [
    {
      title: "New Task",
      description: "Create a scraping task",
      route: "/tasks",
      iconBg: "#dbeafe",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="16" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
      ),
    },
    {
      title: "Templates",
      description: "Browse 55 pre-built scrapers",
      route: "/templates",
      iconBg: "#dcfce7",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
        </svg>
      ),
    },
    {
      title: "Test URL",
      description: "Quick test any URL",
      route: "/scrape-test",
      iconBg: "#f3e8ff",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9333ea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      ),
    },
    {
      title: "Results",
      description: "View extracted data",
      route: "/results",
      iconBg: "#fef3c7",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
    },
    {
      title: "Start Crawl",
      description: "Recursive web crawl",
      route: "/crawl",
      iconBg: "#e0e7ff",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="10" r="4" />
          <path d="M8 10L4 5M16 10L20 5M8 12L3 15M16 12L21 15M9 14L5 20M15 14L19 20" />
        </svg>
      ),
    },
    {
      title: "Web Search",
      description: "Search and extract",
      route: "/search",
      iconBg: "#ecfdf5",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="7" />
          <line x1="16.5" y1="16.5" x2="21" y2="21" />
        </svg>
      ),
    },
    {
      title: "MCP Setup",
      description: "Connect to AI agents",
      route: "/mcp",
      iconBg: "#f0fdf4",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 2v5M15 2v5M6 7h12v4.5a6 6 0 01-12 0V7z" />
          <line x1="12" y1="17.5" x2="12" y2="22" />
        </svg>
      ),
    },
  ];

  const handleQuickAction = useCallback(
    (route: string) => {
      navigate(route);
    },
    [navigate],
  );

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Dashboard</h2>
          <p>Overview of your scraping tasks and platform activity.</p>
        </div>
        <div className="page-header-actions" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
            Last refreshed {formatTime(lastRefreshed)}
          </span>
          {healthData && (
            <span
              className={`badge badge--${healthData.status === "healthy" ? "success" : "warning"}`}
            >
              <span
                className={`status-dot status-dot--${healthData.status === "healthy" ? "success" : "warning"}`}
              />
              API {healthData.status}
            </span>
          )}
        </div>
      </div>

      <div className="page-body">
        {/* Stat cards */}
        <div className="stats-grid">
          {stats.map((s) => (
            <div
              key={s.label}
              className={`stat-card ${s.variant}`}
            >
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{s.value}</div>
              <div className="stat-sub">{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Quick actions */}
        <div style={{ marginBottom: 24 }}>
          <div className="quick-actions">
            {quickActions.map((action) => (
              <button
                key={action.title}
                className="quick-action"
                onClick={() => handleQuickAction(action.route)}
              >
                <div
                  className="qa-icon"
                  style={{ background: action.iconBg }}
                >
                  {action.icon}
                </div>
                <div>
                  <div className="qa-text">{action.title}</div>
                  <div className="qa-sub">{action.description}</div>
                </div>
              </button>
            ))}
          </div>
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
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
              </div>
              <h3>No Tasks Yet</h3>
              <p>
                Get started by creating your first scraping task or browsing
                pre-built templates for popular websites.
              </p>
              <div className="empty-state-action" style={{ display: "flex", gap: 10, justifyContent: "center" }}>
                <button
                  className="btn btn-primary"
                  onClick={() => navigate("/tasks")}
                >
                  Create a Task
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => navigate("/templates")}
                >
                  Browse Templates
                </button>
              </div>
            </div>
          )}

          {!isLoading && !error && items.length > 0 && <TaskTable tasks={items} />}
        </div>
      </div>
    </>
  );
}
