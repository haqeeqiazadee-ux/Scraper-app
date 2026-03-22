/**
 * RunHistory — Table of past runs for a task.
 * Columns: run_id, started_at, duration, status, records_found, lane_used.
 */

import { StatusBadge } from "./StatusBadge";
import type { RunListItem } from "../api/types";

interface RunHistoryProps {
  runs: RunListItem[];
  isLoading?: boolean;
}

function formatDate(iso: string | null): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleString();
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.floor((ms % 60_000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function truncateId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 8)}...`;
}

export function RunHistory({ runs, isLoading }: RunHistoryProps) {
  if (isLoading) {
    return <div className="loading">Loading run history...</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="empty-state">
        <h3>No runs yet</h3>
        <p>Execute the task to see run history here.</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Started</th>
            <th>Duration</th>
            <th>Status</th>
            <th>Records</th>
            <th>Lane</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
                title={run.id}
              >
                {truncateId(run.id)}
              </td>
              <td>{formatDate(run.started_at)}</td>
              <td>{formatDuration(run.duration_ms)}</td>
              <td>
                <StatusBadge status={run.status} />
              </td>
              <td>{run.records_found}</td>
              <td>
                <span className="badge badge--queued">{run.lane}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
