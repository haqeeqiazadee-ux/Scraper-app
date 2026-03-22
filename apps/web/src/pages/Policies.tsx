import { useQuery } from "@tanstack/react-query";
import { policies } from "../api/client";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function Policies() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["policies"],
    queryFn: () => policies.list({ limit: 50 }),
  });

  const items = data?.items ?? [];

  return (
    <>
      <div className="page-header">
        <h2>Policies</h2>
        <p>Configure extraction policies for different target domains.</p>
      </div>
      <div className="page-body">
        <div className="card">
          <div className="card-header">
            <h3>{data?.total ?? 0} Policies</h3>
            {/* Create button placeholder for WEB-002 */}
          </div>

          {isLoading && <div className="loading">Loading policies...</div>}
          {error && (
            <div className="empty-state">
              <p>Failed to load policies.</p>
            </div>
          )}

          {!isLoading && !error && items.length === 0 && (
            <div className="empty-state">
              <h3>No policies defined</h3>
              <p>Policies let you control how specific domains are scraped.</p>
            </div>
          )}

          {!isLoading && !error && items.length > 0 && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Lane</th>
                    <th>Domains</th>
                    <th>Timeout</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 500 }}>{p.name}</td>
                      <td>
                        <span className="badge badge--queued">{p.preferred_lane}</span>
                      </td>
                      <td>
                        {p.target_domains.length > 0
                          ? p.target_domains.join(", ")
                          : "Any"}
                      </td>
                      <td>{(p.timeout_ms / 1000).toFixed(0)}s</td>
                      <td>{formatDate(p.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
