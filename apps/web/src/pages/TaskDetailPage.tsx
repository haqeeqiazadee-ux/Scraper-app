/**
 * TaskDetailPage — Page combining TaskDetail + RunHistory.
 * Fetches task, results, and run history data.
 */

import { useParams, Link } from "react-router-dom";
import { useTask, useTaskResults, useTaskRuns } from "../hooks/useTasks";
import { TaskDetail } from "../components/TaskDetail";
import { RunHistory } from "../components/RunHistory";

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();

  const {
    data: task,
    isLoading: taskLoading,
    error: taskError,
  } = useTask(taskId);

  const { data: resultsData } = useTaskResults(taskId);

  const { data: runsData, isLoading: runsLoading } = useTaskRuns(taskId);

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
          <Link
            to="/tasks"
            className="btn btn-secondary"
            style={{ marginTop: 16 }}
          >
            Back to Tasks
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <h2>{task.name || "Task Detail"}</h2>
        <p>
          <Link to="/tasks">Tasks</Link> / {task.name || task.id}
        </p>
      </div>
      <div className="page-body">
        <TaskDetail
          task={task}
          results={resultsData?.items ?? []}
          resultsTotal={resultsData?.total ?? 0}
        />

        {/* Run History section */}
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-header">
            <h3>Run History ({runsData?.total ?? 0})</h3>
          </div>
          <RunHistory
            runs={runsData?.items ?? []}
            isLoading={runsLoading}
          />
        </div>
      </div>
    </>
  );
}
