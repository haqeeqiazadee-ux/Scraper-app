import { Link } from "react-router-dom";
import type { TaskListItem } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface TaskTableProps {
  tasks: TaskListItem[];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function TaskTable({ tasks }: TaskTableProps) {
  if (tasks.length === 0) {
    return (
      <div className="empty-state">
        <h3>No tasks found</h3>
        <p>Create a new scraping task to get started.</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>URL</th>
            <th>Type</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td className="url-cell" title={task.url}>
                {task.url}
              </td>
              <td>{task.task_type}</td>
              <td>{task.priority}</td>
              <td>
                <StatusBadge status={task.status} />
              </td>
              <td>{formatDate(task.created_at)}</td>
              <td>
                <Link to={`/tasks/${task.id}`} className="btn btn-secondary btn-sm">
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
