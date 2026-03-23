/**
 * SchedulesPage — Manage cron/interval scraping schedules.
 *
 * Features:
 * - Table of schedules with URL, cron expression, type badge, status toggle
 * - Last fired relative time, created date
 * - Delete with inline confirm
 * - ScheduleForm modal for creation
 * - Empty state when no schedules
 */

import { useState, useCallback } from "react";
import {
  useScheduleList,
  useCreateSchedule,
  useDeleteSchedule,
} from "../hooks/useSchedules";
import { ScheduleForm } from "../components/ScheduleForm";
import type { ScheduleResponse } from "../api/types";

/* ── Helpers ── */

function relativeTime(iso: string | null): string {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function truncateUrl(url: string, maxLen = 52): string {
  if (url.length <= maxLen) return url;
  return url.slice(0, maxLen) + "…";
}

function scheduleTypeBadgeClass(type: ScheduleResponse["schedule_type"]): string {
  switch (type) {
    case "cron":
      return "badge--queued";
    case "interval":
      return "badge--running";
    case "one_time":
      return "badge--pending";
    default:
      return "badge--cancelled";
  }
}

/* ── Component ── */

export function SchedulesPage() {
  const [showForm, setShowForm] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useScheduleList();
  const deleteMutation = useDeleteSchedule();
  const createScheduleMutation = useCreateSchedule();

  const rawData = data as unknown;
  const items: ScheduleResponse[] = Array.isArray(rawData)
    ? (rawData as ScheduleResponse[])
    : ((rawData as { items?: ScheduleResponse[] } | undefined)?.items ?? []);

  const handleDelete = useCallback(
    (scheduleId: string) => {
      deleteMutation.mutate(scheduleId, {
        onSuccess: () => setConfirmDeleteId(null),
      });
    },
    [deleteMutation],
  );

  const handleFormClose = useCallback(() => {
    setShowForm(false);
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Schedules</h2>
        <p>Automate scraping tasks with cron expressions or fixed intervals.</p>
      </div>

      <div className="page-body">
        {/* Toolbar */}
        <div className="toolbar">
          <div />
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            + Create Schedule
          </button>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>
              {Array.isArray(items) ? items.length : 0} schedule
              {Array.isArray(items) && items.length !== 1 ? "s" : ""}
            </h3>
          </div>

          {/* Loading */}
          {isLoading && <div className="loading">Loading schedules…</div>}

          {/* Error */}
          {error && !isLoading && (
            <div className="empty-state">
              <h3>Failed to load schedules</h3>
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
              <h3>No schedules yet</h3>
              <p>
                Create a schedule to run scraping tasks automatically on a
                recurring basis.
              </p>
              <button
                className="btn btn-primary"
                style={{ marginTop: 16 }}
                onClick={() => setShowForm(true)}
              >
                + Create Schedule
              </button>
            </div>
          )}

          {/* Table */}
          {!isLoading && !error && items.length > 0 && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>Schedule</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Last Fired</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => (
                    <tr key={s.schedule_id}>
                      {/* URL */}
                      <td>
                        <span
                          className="url-cell"
                          title={s.url}
                          style={{ display: "block", maxWidth: 280 }}
                        >
                          {truncateUrl(s.url)}
                        </span>
                      </td>

                      {/* Schedule expression */}
                      <td>
                        <code
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 12,
                            background: "var(--color-bg)",
                            padding: "2px 6px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--color-border)",
                          }}
                        >
                          {s.schedule}
                        </code>
                      </td>

                      {/* Type badge */}
                      <td>
                        <span
                          className={`badge ${scheduleTypeBadgeClass(s.schedule_type)}`}
                          style={{ textTransform: "capitalize" }}
                        >
                          {s.schedule_type.replace("_", " ")}
                        </span>
                      </td>

                      {/* Status toggle */}
                      <td>
                        <span
                          className={`badge ${s.active ? "badge--success" : "badge--cancelled"}`}
                        >
                          {s.active ? "Active" : "Paused"}
                        </span>
                      </td>

                      {/* Last fired */}
                      <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                        {relativeTime(s.last_fired)}
                      </td>

                      {/* Created */}
                      <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                        {formatDate(s.created_at)}
                      </td>

                      {/* Actions */}
                      <td>
                        <div className="action-buttons">
                          {confirmDeleteId === s.schedule_id ? (
                            <>
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDelete(s.schedule_id)}
                                disabled={deleteMutation.isPending}
                              >
                                {deleteMutation.isPending ? "…" : "Confirm"}
                              </button>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => setConfirmDeleteId(null)}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => setConfirmDeleteId(s.schedule_id)}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Create Schedule Modal */}
      <ScheduleForm
        open={showForm}
        onClose={handleFormClose}
        onSubmit={(req) => {
          createScheduleMutation.mutate(req, {
            onSuccess: () => handleFormClose(),
          });
        }}
      />
    </>
  );
}
