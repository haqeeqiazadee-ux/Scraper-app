import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { tasks } from "../api/client";
import { TaskTable } from "../components/TaskTable";


const STATUS_FILTERS: { label: string; value: string | undefined }[] = [
  { label: "All", value: undefined },
  { label: "Pending", value: "pending" },
  { label: "Running", value: "running" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
];

const PAGE_SIZE = 20;

export function Tasks() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["tasks", statusFilter, page],
    queryFn: () =>
      tasks.list({
        status: statusFilter,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <>
      <div className="page-header">
        <h2>Tasks</h2>
        <p>Manage and monitor your scraping tasks.</p>
      </div>
      <div className="page-body">
        {/* Filters */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.label}
              className={`btn btn-sm ${statusFilter === f.value ? "btn-primary" : "btn-secondary"}`}
              onClick={() => {
                setStatusFilter(f.value);
                setPage(0);
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>
              {total} task{total !== 1 ? "s" : ""}
              {statusFilter ? ` (${statusFilter})` : ""}
            </h3>
          </div>
          {isLoading && <div className="loading">Loading...</div>}
          {error && (
            <div className="empty-state">
              <p>Failed to load tasks.</p>
            </div>
          )}
          {!isLoading && !error && <TaskTable tasks={items} />}

          {/* Pagination */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "12px 0 0",
                borderTop: "1px solid var(--color-border)",
                marginTop: 12,
              }}
            >
              <button
                className="btn btn-secondary btn-sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
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
    </>
  );
}
