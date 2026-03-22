/**
 * Policies page with listing, create, and delete functionality.
 * Uses usePolicies hooks for data management.
 */

import { useState, useCallback } from "react";
import {
  usePolicyList,
  useCreatePolicy,
  useDeletePolicy,
} from "../hooks/usePolicies";
import type { PolicyCreate, LanePreference } from "../api/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const LANE_OPTIONS: { value: LanePreference; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "api", label: "API" },
  { value: "http", label: "HTTP" },
  { value: "browser", label: "Browser" },
  { value: "hard_target", label: "Hard Target" },
];

export function Policies() {
  const [showForm, setShowForm] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data, isLoading, error } = usePolicyList({ limit: 50 });
  const createMutation = useCreatePolicy();
  const deleteMutation = useDeletePolicy();

  const items = data?.items ?? [];

  // Form state
  const [formName, setFormName] = useState("");
  const [formLane, setFormLane] = useState<LanePreference>("auto");
  const [formDomains, setFormDomains] = useState("");
  const [formTimeout, setFormTimeout] = useState(30000);
  const [formError, setFormError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setFormName("");
    setFormLane("auto");
    setFormDomains("");
    setFormTimeout(30000);
    setFormError(null);
  }, []);

  const handleCreate = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!formName.trim()) {
        setFormError("Policy name is required.");
        return;
      }

      const domains = formDomains
        .split(",")
        .map((d) => d.trim())
        .filter((d) => d.length > 0);

      const data: PolicyCreate = {
        name: formName.trim(),
        preferred_lane: formLane,
        target_domains: domains,
        timeout_ms: formTimeout,
      };

      createMutation.mutate(data, {
        onSuccess: () => {
          resetForm();
          setShowForm(false);
        },
        onError: (err) => {
          setFormError(
            err instanceof Error ? err.message : "Failed to create policy.",
          );
        },
      });
    },
    [formName, formLane, formDomains, formTimeout, createMutation, resetForm],
  );

  const handleDelete = useCallback(
    (policyId: string) => {
      deleteMutation.mutate(policyId, {
        onSuccess: () => setConfirmDeleteId(null),
      });
    },
    [deleteMutation],
  );

  return (
    <>
      <div className="page-header">
        <h2>Policies</h2>
        <p>Configure extraction policies for different target domains.</p>
      </div>
      <div className="page-body">
        {/* Toolbar */}
        <div className="toolbar" style={{ marginBottom: 16 }}>
          <div />
          <button
            className="btn btn-primary"
            onClick={() => {
              resetForm();
              setShowForm(true);
            }}
          >
            + Create Policy
          </button>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>{data?.total ?? 0} Policies</h3>
          </div>

          {isLoading && <div className="loading">Loading policies...</div>}
          {error && (
            <div className="empty-state">
              <p>Failed to load policies. Is the control plane running?</p>
            </div>
          )}

          {!isLoading && !error && items.length === 0 && (
            <div className="empty-state">
              <h3>No policies defined</h3>
              <p>
                Policies let you control how specific domains are scraped.
              </p>
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
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 500 }}>{p.name}</td>
                      <td>
                        <span className="badge badge--queued">
                          {p.preferred_lane}
                        </span>
                      </td>
                      <td>
                        {p.target_domains.length > 0
                          ? p.target_domains.join(", ")
                          : "Any"}
                      </td>
                      <td>{(p.timeout_ms / 1000).toFixed(0)}s</td>
                      <td>{formatDate(p.created_at)}</td>
                      <td>
                        <div className="action-buttons">
                          {confirmDeleteId === p.id ? (
                            <>
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDelete(p.id)}
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
                              onClick={() => setConfirmDeleteId(p.id)}
                              title="Delete policy"
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
          )}
        </div>
      </div>

      {/* Create Policy Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <form onSubmit={handleCreate} className="task-form">
              <div className="form-header">
                <h3>Create Policy</h3>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setShowForm(false)}
                  disabled={createMutation.isPending}
                >
                  Cancel
                </button>
              </div>

              {formError && (
                <div className="form-error-banner">{formError}</div>
              )}

              <div className="form-group">
                <label htmlFor="policy-name">Name</label>
                <input
                  id="policy-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. E-commerce scraper"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  disabled={createMutation.isPending}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label htmlFor="policy-lane">Preferred Lane</label>
                <select
                  id="policy-lane"
                  className="form-input"
                  value={formLane}
                  onChange={(e) =>
                    setFormLane(e.target.value as LanePreference)
                  }
                  disabled={createMutation.isPending}
                >
                  {LANE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="policy-domains">Target Domains</label>
                <input
                  id="policy-domains"
                  type="text"
                  className="form-input"
                  placeholder="example.com, shop.example.com"
                  value={formDomains}
                  onChange={(e) => setFormDomains(e.target.value)}
                  disabled={createMutation.isPending}
                />
                <span className="form-hint">
                  Comma-separated list of domains. Leave empty for any domain.
                </span>
              </div>

              <div className="form-group">
                <label htmlFor="policy-timeout">
                  Timeout ({(formTimeout / 1000).toFixed(0)}s)
                </label>
                <input
                  id="policy-timeout"
                  type="range"
                  min={5000}
                  max={120000}
                  step={5000}
                  className="form-range"
                  value={formTimeout}
                  onChange={(e) => setFormTimeout(Number(e.target.value))}
                  disabled={createMutation.isPending}
                />
                <div className="form-range-labels">
                  <span>5s</span>
                  <span>120s</span>
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowForm(false)}
                  disabled={createMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createMutation.isPending}
                >
                  {createMutation.isPending ? "Creating..." : "Create Policy"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
