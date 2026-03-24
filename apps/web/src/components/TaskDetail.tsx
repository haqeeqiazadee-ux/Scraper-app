/**
 * TaskDetail — Detail view for a single task showing config, run history,
 * and latest results. Fetches from GET /api/v1/tasks/{id}.
 */

import { Link } from "react-router-dom";
import { StatusBadge } from "./StatusBadge";
import { useCancelTask, useExecuteTask } from "../hooks/useTasks";
import type { Task, ResultListItem } from "../api/types";

interface TaskDetailProps {
  task: Task;
  results: ResultListItem[];
  resultsTotal: number;
}

function formatDate(iso: string | null): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleString();
}

export function TaskDetail({ task, results, resultsTotal }: TaskDetailProps) {
  const cancelMutation = useCancelTask();
  const executeMutation = useExecuteTask();

  const canCancel =
    task.status === "pending" ||
    task.status === "queued" ||
    task.status === "running";

  const canRun =
    task.status !== "running" &&
    task.status !== "completed" &&
    task.status !== "cancelled";

  return (
    <div className="detail-grid">
      {/* Info card */}
      <div className="card">
        <div className="card-header">
          <h3>Task Configuration</h3>
          <div className="action-buttons">
            {canRun && (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => executeMutation.mutate(task.id)}
                disabled={executeMutation.isPending}
              >
                {executeMutation.isPending ? "Starting..." : "Run Now"}
              </button>
            )}
            {canCancel && (
              <button
                className="btn btn-danger btn-sm"
                onClick={() => cancelMutation.mutate(task.id)}
                disabled={cancelMutation.isPending}
              >
                {cancelMutation.isPending ? "Cancelling..." : "Cancel"}
              </button>
            )}
          </div>
        </div>

        <div className="detail-row">
          <span className="detail-label">ID</span>
          <span
            className="detail-value"
            style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
          >
            {task.id}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Name</span>
          <span className="detail-value">{task.name || "(unnamed)"}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">URL</span>
          <span className="detail-value" style={{ wordBreak: "break-all" }}>
            {task.url}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Status</span>
          <span className="detail-value">
            <StatusBadge status={task.status} />
          </span>
        </div>
        {task.status === "failed" && task.metadata && "last_error" in task.metadata && (
          <div className="detail-row">
            <span className="detail-label">Error</span>
            <span
              className="detail-value"
              style={{ color: "var(--color-danger, #dc3545)", fontFamily: "var(--font-mono)", fontSize: 12, wordBreak: "break-all" }}
            >
              {String(task.metadata.last_error)}
            </span>
          </div>
        )}
        <div className="detail-row">
          <span className="detail-label">Type</span>
          <span className="detail-value">{task.task_type}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Extraction</span>
          <span className="detail-value">{task.extraction_type ?? "auto"}</span>
        </div>
        {task.selectors && task.selectors.length > 0 && (
          <div className="detail-row">
            <span className="detail-label">Selectors</span>
            <span
              className="detail-value"
              style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
            >
              {task.selectors.join(", ")}
            </span>
          </div>
        )}
        <div className="detail-row">
          <span className="detail-label">Priority</span>
          <span className="detail-value">{task.priority}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Policy</span>
          <span className="detail-value">{task.policy_id ?? "None"}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Schedule</span>
          <span className="detail-value">{task.schedule ?? "One-time"}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Last Run</span>
          <span className="detail-value">{formatDate(task.last_run)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Next Run</span>
          <span className="detail-value">{formatDate(task.next_run)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Created</span>
          <span className="detail-value">{formatDate(task.created_at)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Updated</span>
          <span className="detail-value">{formatDate(task.updated_at)}</span>
        </div>
      </div>

      {/* Results card */}
      <div className="card">
        <div className="card-header">
          <h3>Latest Results ({resultsTotal})</h3>
        </div>
        {results.length === 0 ? (
          <div className="empty-state">
            <p>No results yet. Run the task to generate results.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Items</th>
                  <th>Confidence</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id}>
                    <td>{r.extraction_method}</td>
                    <td>{r.item_count}</td>
                    <td>{(r.confidence * 100).toFixed(0)}%</td>
                    <td>{formatDate(r.created_at)}</td>
                    <td>
                      <Link
                        to={`/results?id=${r.id}`}
                        className="btn btn-secondary btn-sm"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
