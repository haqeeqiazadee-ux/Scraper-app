/**
 * RouteTesterPage — Dry-run the execution router against any URL.
 *
 * Features:
 * - Prominent URL input + optional policy dropdown + "Test Route" button
 * - RouteVisualizer when a decision is available
 * - Per-lane explanation text
 * - History of last 5 tests (local state only, no persistence)
 */

import { useState, useCallback, useRef } from "react";
import { useDryRunRoute } from "../hooks/useRouting";
import { usePolicyList } from "../hooks/usePolicies";
import { RouteVisualizer } from "../components/RouteVisualizer";
import type { RouteDecision } from "../api/types";

/* ── Lane explanations ── */

const LANE_EXPLANATIONS: Record<string, string> = {
  http: "Plain HTTP fetch via requests library. Fastest and cheapest. Best for static pages and APIs that return JSON directly.",
  browser:
    "Full Playwright browser session. Handles JavaScript-heavy SPAs, infinite scroll, and sites that require human-like interaction.",
  hard_target:
    "Stealth browser with fingerprint randomisation, residential proxies, and human behaviour emulation. Used when standard browser is blocked.",
  api: "Direct API endpoint call — bypasses HTML rendering entirely. Used when the target exposes a documented API.",
};

/* ── Types ── */

interface HistoryEntry {
  url: string;
  policyId: string | null;
  decision: RouteDecision;
  testedAt: Date;
}

/* ── Component ── */

export function RouteTesterPage() {
  const [url, setUrl] = useState("");
  const [policyId, setPolicyId] = useState<string>("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [currentDecision, setCurrentDecision] = useState<RouteDecision | null>(
    null,
  );
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Policies for the dropdown
  const { data: policiesData } = usePolicyList({ limit: 50 });
  const policies = policiesData?.items ?? [];

  // Dry-run mutation
  const dryRunMutation = useDryRunRoute();

  const handleTest = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      setUrlError(null);

      // Validate URL
      const trimmed = url.trim();
      if (!trimmed) {
        setUrlError("Enter a URL to test.");
        inputRef.current?.focus();
        return;
      }
      try {
        new URL(trimmed);
      } catch {
        setUrlError("Enter a valid absolute URL (e.g. https://example.com).");
        inputRef.current?.focus();
        return;
      }

      dryRunMutation.mutate(
        { url: trimmed, policyId: policyId || undefined },
        {
          onSuccess: (response) => {
            const decision = response.route;
            setCurrentDecision(decision);
            setHistory((prev) => {
              const entry: HistoryEntry = {
                url: trimmed,
                policyId: policyId || null,
                decision,
                testedAt: new Date(),
              };
              // Keep last 5 (most recent first)
              return [entry, ...prev].slice(0, 5);
            });
          },
        },
      );
    },
    [url, policyId, dryRunMutation],
  );

  const laneExplanation =
    currentDecision && LANE_EXPLANATIONS[currentDecision.lane.toLowerCase()];

  return (
    <>
      <div className="page-header">
        <h2>Route Tester</h2>
        <p>
          Preview which execution lane the router would select for any URL —
          without running an actual scrape.
        </p>
      </div>

      <div className="page-body">
        {/* ── Test form ── */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <h3>Test a URL</h3>
          </div>

          <form onSubmit={handleTest}>
            {/* URL input */}
            <div className="form-group">
              <label htmlFor="rt-url">Target URL</label>
              <input
                id="rt-url"
                ref={inputRef}
                type="url"
                className={`form-input${urlError ? " form-input--error" : ""}`}
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (urlError) setUrlError(null);
                }}
                placeholder="https://example.com/products"
                autoFocus
                style={{ fontSize: 15, padding: "10px 14px" }}
                disabled={dryRunMutation.isPending}
              />
              {urlError && (
                <span className="form-error">{urlError}</span>
              )}
            </div>

            {/* Policy dropdown (optional) */}
            <div className="form-group">
              <label htmlFor="rt-policy">
                Policy{" "}
                <span
                  style={{
                    fontWeight: 400,
                    color: "var(--color-text-secondary)",
                  }}
                >
                  (optional)
                </span>
              </label>
              <select
                id="rt-policy"
                className="form-input"
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
                disabled={dryRunMutation.isPending}
              >
                <option value="">— Auto (no policy) —</option>
                {policies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.target_domains.length > 0
                      ? ` (${p.target_domains.join(", ")})`
                      : ""}
                  </option>
                ))}
              </select>
              <span className="form-hint">
                Selecting a policy applies its lane preference and domain
                rules to the routing decision.
              </span>
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={dryRunMutation.isPending || !url.trim()}
              style={{ minWidth: 140 }}
            >
              {dryRunMutation.isPending ? "Testing…" : "Test Route"}
            </button>

            {/* Mutation error */}
            {dryRunMutation.isError && (
              <div
                className="form-error-banner"
                style={{ marginTop: 12 }}
              >
                {dryRunMutation.error instanceof Error
                  ? dryRunMutation.error.message
                  : "Failed to run route test. Is the control plane running?"}
              </div>
            )}
          </form>
        </div>

        {/* ── Result ── */}
        {currentDecision && (
          <div style={{ marginBottom: 24 }}>
            <h3
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 12,
              }}
            >
              Route Decision
            </h3>

            <RouteVisualizer decision={currentDecision} />

            {/* Lane explanation */}
            {laneExplanation && (
              <div
                style={{
                  marginTop: 12,
                  padding: "12px 16px",
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: 13,
                  color: "var(--color-text-secondary)",
                  lineHeight: 1.6,
                }}
              >
                <span
                  style={{
                    fontWeight: 600,
                    color: "var(--color-text)",
                    textTransform: "capitalize",
                  }}
                >
                  {currentDecision.lane} lane:
                </span>{" "}
                {laneExplanation}
              </div>
            )}
          </div>
        )}

        {/* ── History ── */}
        {history.length > 0 && (
          <div>
            <h3
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 12,
              }}
            >
              Recent Tests
            </h3>

            <div className="card">
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>URL</th>
                      <th>Selected Lane</th>
                      <th>Confidence</th>
                      <th>Fallbacks</th>
                      <th>Tested</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((entry, idx) => {
                      const confPct = Math.round(
                        entry.decision.confidence * 100,
                      );
                      const confColor =
                        entry.decision.confidence >= 0.8
                          ? "var(--color-success)"
                          : entry.decision.confidence >= 0.5
                          ? "var(--color-warning)"
                          : "var(--color-error)";
                      const mins = Math.floor(
                        (Date.now() - entry.testedAt.getTime()) / 60_000,
                      );
                      const timeLabel =
                        mins < 1
                          ? "Just now"
                          : mins === 1
                          ? "1m ago"
                          : `${mins}m ago`;

                      return (
                        <tr
                          key={idx}
                          style={{
                            cursor: "pointer",
                            opacity: idx === 0 ? 1 : 0.75,
                          }}
                          onClick={() => {
                            setCurrentDecision(entry.decision);
                            setUrl(entry.url);
                            setPolicyId(entry.policyId ?? "");
                            window.scrollTo({ top: 0, behavior: "smooth" });
                          }}
                          title="Click to reload this result"
                        >
                          <td>
                            <span
                              className="url-cell"
                              style={{
                                display: "block",
                                maxWidth: 320,
                                fontFamily: "var(--font-mono)",
                                fontSize: 12,
                              }}
                              title={entry.url}
                            >
                              {entry.url.length > 60
                                ? entry.url.slice(0, 60) + "…"
                                : entry.url}
                            </span>
                          </td>
                          <td>
                            <span className="badge badge--queued">
                              {entry.decision.lane}
                            </span>
                          </td>
                          <td>
                            <span
                              style={{
                                fontSize: 13,
                                fontWeight: 600,
                                color: confColor,
                              }}
                            >
                              {confPct}%
                            </span>
                          </td>
                          <td style={{ fontSize: 13 }}>
                            {entry.decision.fallback_lanes.length > 0 ? (
                              <span
                                style={{
                                  color: "var(--color-text-secondary)",
                                  fontFamily: "var(--font-mono)",
                                  fontSize: 12,
                                }}
                              >
                                {entry.decision.fallback_lanes.join(" → ")}
                              </span>
                            ) : (
                              <span
                                style={{
                                  color: "var(--color-text-secondary)",
                                }}
                              >
                                None
                              </span>
                            )}
                          </td>
                          <td
                            style={{
                              color: "var(--color-text-secondary)",
                              fontSize: 13,
                            }}
                          >
                            {timeLabel}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Empty state — no tests yet */}
        {history.length === 0 && !currentDecision && (
          <div className="empty-state">
            <h3>No tests run yet</h3>
            <p>
              Enter a URL above and click <strong>Test Route</strong> to see
              which execution lane the router would select.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
