/**
 * TasksPage — Page combining TaskTable + TaskForm in a modal/drawer pattern.
 *
 * Features:
 * - Status filter buttons
 * - Pagination
 * - "Create Task" button that opens the TaskForm in a modal overlay
 * - "Edit" action that opens TaskForm pre-filled with existing task data
 */

import { useState, useCallback } from "react";
import { useTaskList, useTask } from "../hooks/useTasks";
import { TaskTable } from "../components/TaskTable";
import { TaskForm } from "../components/TaskForm";
import type { TaskStatus } from "../api/types";

const STATUS_FILTERS: { label: string; value: string | undefined }[] = [
  { label: "All", value: undefined },
  { label: "Pending", value: "pending" },
  { label: "Running", value: "running" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
];

const PAGE_SIZE = 20;

export function TasksPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    undefined,
  );
  const [page, setPage] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);

  const { data, isLoading, error } = useTaskList({
    status: statusFilter,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  // Fetch the task being edited (if any)
  const { data: editingTask } = useTask(editingTaskId ?? undefined);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleCreateClick = useCallback(() => {
    setEditingTaskId(null);
    setShowForm(true);
  }, []);

  const handleEditClick = useCallback((taskId: string) => {
    setEditingTaskId(taskId);
    setShowForm(true);
  }, []);

  const handleFormClose = useCallback(() => {
    setShowForm(false);
    setEditingTaskId(null);
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Tasks</h2>
        <p>Manage and monitor your scraping tasks.</p>
      </div>
      <div className="page-body">
        {/* Toolbar: filters + create button */}
        <div className="toolbar">
          <div className="filter-bar">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.label}
                className={`btn btn-sm ${
                  statusFilter === f.value ? "btn-primary" : "btn-secondary"
                }`}
                onClick={() => {
                  setStatusFilter(f.value);
                  setPage(0);
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button className="btn btn-primary" onClick={handleCreateClick}>
            + Create Task
          </button>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>
              {total} task{total !== 1 ? "s" : ""}
              {statusFilter ? ` (${statusFilter})` : ""}
            </h3>
          </div>

          {isLoading && <div className="loading">Loading tasks...</div>}

          {error && (
            <div className="empty-state">
              <p>Failed to load tasks. Is the control plane running?</p>
            </div>
          )}

          {!isLoading && !error && (
            <TaskTable tasks={items} onEdit={handleEditClick} />
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {page + 1} of {totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Modal overlay for TaskForm */}
      {showForm && (
        <div className="modal-overlay" onClick={handleFormClose}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <TaskForm
              task={editingTaskId && editingTask ? editingTask : undefined}
              onClose={handleFormClose}
            />
          </div>
        </div>
      )}
    </>
  );
}
