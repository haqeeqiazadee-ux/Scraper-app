/**
 * TaskTable — Sortable table listing tasks with columns:
 * name, url, status (badge), last_run, next_run, actions (edit/delete/run).
 *
 * Includes pagination controls and column sorting.
 */

import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import type { TaskListItem } from "../api/types";
import { StatusBadge } from "./StatusBadge";
import { useDeleteTask, useExecuteTask } from "../hooks/useTasks";

interface TaskTableProps {
  tasks: TaskListItem[];
  /** Called when the user clicks "Edit" on a row. */
  onEdit?: (taskId: string) => void;
}

type SortField = "name" | "url" | "status" | "last_run" | "next_run" | "created_at";
type SortDir = "asc" | "desc";

function formatDate(iso: string | null): string {
  if (!iso) return "--";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function compareValues(a: string | null, b: string | null, dir: SortDir): number {
  const av = a ?? "";
  const bv = b ?? "";
  const cmp = av.localeCompare(bv);
  return dir === "asc" ? cmp : -cmp;
}

export function TaskTable({ tasks, onEdit }: TaskTableProps) {
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const deleteMutation = useDeleteTask();
  const executeMutation = useExecuteTask();

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortField(field);
        setSortDir("asc");
      }
    },
    [sortField],
  );

  const handleDelete = useCallback(
    (taskId: string) => {
      deleteMutation.mutate(taskId, {
        onSuccess: () => setConfirmDeleteId(null),
      });
    },
    [deleteMutation],
  );

  const handleExecute = useCallback(
    (taskId: string) => {
      executeMutation.mutate(taskId);
    },
    [executeMutation],
  );

  if (tasks.length === 0) {
    return (
      <div className="empty-state">
        <h3>No tasks found</h3>
        <p>Create a new scraping task to get started.</p>
      </div>
    );
  }

  // Sort the tasks
  const sorted = [...tasks].sort((a, b) => {
    switch (sortField) {
      case "name":
        return compareValues(a.name, b.name, sortDir);
      case "url":
        return compareValues(a.url, b.url, sortDir);
      case "status":
        return compareValues(a.status, b.status, sortDir);
      case "last_run":
        return compareValues(a.last_run, b.last_run, sortDir);
      case "next_run":
        return compareValues(a.next_run, b.next_run, sortDir);
      case "created_at":
        return compareValues(a.created_at, b.created_at, sortDir);
      default:
        return 0;
    }
  });

  function sortIndicator(field: SortField): string {
    if (sortField !== field) return "";
    return sortDir === "asc" ? " \u2191" : " \u2193";
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th
              className="sortable-th"
              onClick={() => handleSort("name")}
            >
              Name{sortIndicator("name")}
            </th>
            <th
              className="sortable-th"
              onClick={() => handleSort("url")}
            >
              URL{sortIndicator("url")}
            </th>
            <th
              className="sortable-th"
              onClick={() => handleSort("status")}
            >
              Status{sortIndicator("status")}
            </th>
            <th
              className="sortable-th"
              onClick={() => handleSort("last_run")}
            >
              Last Run{sortIndicator("last_run")}
            </th>
            <th
              className="sortable-th"
              onClick={() => handleSort("next_run")}
            >
              Next Run{sortIndicator("next_run")}
            </th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((task) => (
            <tr key={task.id}>
              <td style={{ fontWeight: 500 }}>
                <Link to={`/tasks/${task.id}`}>{task.name || "(unnamed)"}</Link>
              </td>
              <td className="url-cell" title={task.url}>
                {task.url}
              </td>
              <td>
                <StatusBadge status={task.status} />
              </td>
              <td>{formatDate(task.last_run)}</td>
              <td>{formatDate(task.next_run)}</td>
              <td>
                <div className="action-buttons">
                  {onEdit && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onEdit(task.id)}
                      title="Edit task"
                    >
                      Edit
                    </button>
                  )}
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleExecute(task.id)}
                    disabled={
                      executeMutation.isPending ||
                      task.status === "running" ||
                      task.status === "completed" ||
                      task.status === "cancelled"
                    }
                    title="Run now"
                  >
                    Run
                  </button>
                  {confirmDeleteId === task.id ? (
                    <>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(task.id)}
                        disabled={deleteMutation.isPending}
                      >
                        {deleteMutation.isPending ? "..." : "Confirm"}
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => setConfirmDeleteId(null)}
                      >
                        No
                      </button>
                    </>
                  ) : (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => setConfirmDeleteId(task.id)}
                      title="Delete task"
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
  );
}
