import type { TaskStatus, RunStatus } from "../api/types";

type BadgeStatus = TaskStatus | RunStatus;

interface StatusBadgeProps {
  status: BadgeStatus;
}

const LABELS: Record<string, string> = {
  pending: "Pending",
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  success: "Success",
  timeout: "Timeout",
  blocked: "Blocked",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const label = LABELS[status] ?? status;
  return <span className={`badge badge--${status}`}>{label}</span>;
}
