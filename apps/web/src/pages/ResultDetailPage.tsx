/**
 * ResultDetailPage — Page for single result detail.
 * Route: /results/:id
 */

import { useParams, Link } from "react-router-dom";
import { useResult } from "../hooks/useResults";
import { ResultDetail } from "../components/ResultDetail";

export function ResultDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: result, isLoading, error } = useResult(id);

  if (isLoading) {
    return (
      <>
        <div className="page-header">
          <h2>Result Detail</h2>
          <p>
            <Link to="/results">Results</Link> / Loading...
          </p>
        </div>
        <div className="page-body">
          <div className="loading">Loading result...</div>
        </div>
      </>
    );
  }

  if (error || !result) {
    return (
      <>
        <div className="page-header">
          <h2>Result Detail</h2>
          <p>
            <Link to="/results">Results</Link>
          </p>
        </div>
        <div className="page-body">
          <div className="card">
            <div className="empty-state">
              <h3>Result not found</h3>
              <p>The requested result does not exist or you lack access.</p>
              <Link
                to="/results"
                className="btn btn-secondary"
                style={{ marginTop: 16, display: "inline-flex" }}
              >
                Back to Results
              </Link>
            </div>
          </div>
        </div>
      </>
    );
  }

  const apiBase = import.meta.env.VITE_API_URL ?? "/api/v1";

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Result Detail</h2>
          <p>
            <Link to="/results">Results</Link> / {result.id}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <a href={`${apiBase}/tasks/${result.task_id}/export/csv`} className="btn btn-primary btn-sm" download>
            Download CSV
          </a>
          <a href={`${apiBase}/tasks/${result.task_id}/export/json`} className="btn btn-secondary btn-sm" download>
            Download JSON
          </a>
          <a href={`${apiBase}/tasks/${result.task_id}/export/xlsx`} className="btn btn-secondary btn-sm" download>
            Download Excel
          </a>
        </div>
      </div>
      <div className="page-body">
        <ResultDetail result={result} />
      </div>
    </>
  );
}
