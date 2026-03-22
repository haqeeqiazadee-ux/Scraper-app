import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasks } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

function formatDate(iso: string | null): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleString();
}

export function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const queryClient = useQueryClient();

  const {
    data: task,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => tasks.get(taskId!),
    enabled: !!taskId,
  });

  const { data: resultsData } = useQuery({
    queryKey: ["task-results", taskId],
    queryFn: () => tasks.results(taskId!),
    enabled: !!taskId,
  });

  const cancelMutation = useMutation({
    mutationFn: () => tasks.cancel(taskId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  if (isLoading) {
    return (
      <div className="page-body">
        <div className="loading">Loading task...</div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="page-body">
        <div className="empty-state">
          <h3>Task not found</h3>
          <p>The requested task does not exist or you lack access.</p>
          <Link to="/tasks" className="btn btn-secondary" style={{ marginTop: 16 }}>
            Back to Tasks
          </Link>
        </div>
      </div>
    );
  }

  const canCancel = task.status === "pending" || task.status === "queued" || task.status === "running";

  return (
    <>
      <div className="page-header">
        <h2>Task Detail</h2>
        <p>
          <Link to="/tasks">Tasks</Link> / {task.id}
        </p>
      </div>
      <div className="page-body">
        <div className="detail-grid">
          {/* Info card */}
          <div className="card">
            <div className="card-header">
              <h3>Task Info</h3>
              {canCancel && (
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? "Cancelling..." : "Cancel Task"}
                </button>
              )}
            </div>
            <div className="detail-row">
              <span className="detail-label">ID</span>
              <span className="detail-value" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
                {task.id}
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">URL</span>
              <span className="detail-value">{task.url}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Status</span>
              <span className="detail-value">
                <StatusBadge status={task.status} />
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Type</span>
              <span className="detail-value">{task.task_type}</span>
            </div>
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
              <h3>Results ({resultsData?.total ?? 0})</h3>
            </div>
            {!resultsData?.items?.length ? (
              <div className="empty-state">
                <p>No results yet.</p>
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
                    {resultsData.items.map((r) => (
                      <tr key={r.id}>
                        <td>{r.extraction_method}</td>
                        <td>{r.item_count}</td>
                        <td>{(r.confidence * 100).toFixed(0)}%</td>
                        <td>{formatDate(r.created_at)}</td>
                        <td>
                          <Link to={`/results/${r.id}`} className="btn btn-secondary btn-sm">
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
      </div>
    </>
  );
}
