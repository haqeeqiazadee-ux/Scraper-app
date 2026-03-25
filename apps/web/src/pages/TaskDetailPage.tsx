/**
 * TaskDetailPage — Page combining TaskDetail + RunHistory.
 * Fetches task, results, and run history data.
 * Auto-polls every 5 seconds when task is running/queued.
 */

import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useTask, useTaskResults, useTaskRuns, useExecuteTask, useCancelTask, useDeleteTask } from "../hooks/useTasks";
import { TaskDetail } from "../components/TaskDetail";
import { RunHistory } from "../components/RunHistory";

function formatDate(iso: string | null): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleString();
}

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const executeMutation = useExecuteTask();
  const cancelMutation = useCancelTask();
  const deleteMutation = useDeleteTask();

  const {
    data: task,
    isLoading: taskLoading,
    error: taskError,
  } = useTask(taskId, {
    // Poll every 5 seconds when task is actively running or queued
    refetchInterval: taskId ? 5_000 : false,
  });

  const { data: resultsData } = useTaskResults(taskId);

  const { data: runsData, isLoading: runsLoading } = useTaskRuns(taskId);

  const isActive =
    task?.status === "running" || task?.status === "queued";

  const canCancel =
    task?.status === "pending" ||
    task?.status === "queued" ||
    task?.status === "running";

  const canRun =
    task?.status !== "running" &&
    task?.status !== "queued";

  function handleDelete() {
    if (!taskId) return;
    deleteMutation.mutate(taskId, {
      onSuccess: () => navigate("/tasks"),
    });
  }

  if (taskLoading) {
    return (
      <div className="page-body">
        <div className="loading">Loading task...</div>
      </div>
    );
  }

  if (taskError || !task) {
    return (
      <div className="page-body">
        <div className="empty-state">
          <h3>Task not found</h3>
          <p>The requested task does not exist or you lack access.</p>
          <Link to="/tasks" className="btn btn-secondary">
            Back to Tasks
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Breadcrumb */}
      <div className="page-header">
        <p className="breadcrumb">
          <Link to="/tasks" className="breadcrumb-link">Tasks</Link>
          <span className="breadcrumb-separator"> / </span>
          <span className="breadcrumb-current">{task.name || task.id}</span>
          {isActive && (
            <span className="badge badge--running" style={{ marginLeft: 8, fontSize: 11 }}>
              auto-refreshing
            </span>
          )}
        </p>
        <h2>{task.name || "Task Detail"}</h2>
      </div>

      <div className="page-body">
        {/* Action buttons bar */}
        <div className="card">
          <div className="card-header">
            <div className="action-group">
              {/* Status badge — large */}
              <span className={`badge badge--${task.status}`} style={{ fontSize: 14, padding: "6px 16px" }}>
                {task.status.toUpperCase()}
              </span>
            </div>
            <div className="action-group">
              {canRun && (
                <button
                  className="btn btn-primary"
                  onClick={() => executeMutation.mutate(task.id)}
                  disabled={executeMutation.isPending}
                >
                  {executeMutation.isPending ? "Starting..." : "Run Now"}
                </button>
              )}
              {canCancel && (
                <button
                  className="btn btn-danger"
                  onClick={() => cancelMutation.mutate(task.id)}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? "Cancelling..." : "Cancel"}
                </button>
              )}
              {!showDeleteConfirm ? (
                <button
                  className="btn btn-danger"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  Delete
                </button>
              ) : (
                <>
                  <span>Are you sure?</span>
                  <button
                    className="btn btn-danger"
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? "Deleting..." : "Confirm Delete"}
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setShowDeleteConfirm(false)}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Task metadata summary */}
        <div className="card">
          <div className="card-header">
            <h3>Overview</h3>
          </div>
          <div className="detail-row">
            <span className="detail-label">URL</span>
            <span className="detail-value">
              <a href={task.url} target="_blank" rel="noopener noreferrer">
                {task.url}
              </a>
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Created</span>
            <span className="detail-value">{formatDate(task.created_at)}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Last Run</span>
            <span className="detail-value">{formatDate(task.last_run)}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Type</span>
            <span className="detail-value">{task.task_type}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Extraction</span>
            <span className="detail-value">{task.extraction_type ?? "auto"}</span>
          </div>
        </div>

        {/* Full task detail + results */}
        <TaskDetail
          task={task}
          results={resultsData?.items ?? []}
          resultsTotal={resultsData?.total ?? 0}
        />

        {/* Run History section */}
        <div className="card">
          <div className="card-header">
            <h3>Run History ({runsData?.total ?? 0})</h3>
          </div>
          <RunHistory runs={runsData?.items ?? []} isLoading={runsLoading} />
        </div>
      </div>
    </>
  );
}
