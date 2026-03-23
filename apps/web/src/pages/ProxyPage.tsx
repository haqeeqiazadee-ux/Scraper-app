/**
 * ProxyPage — Monitor proxy pool health and performance metrics.
 *
 * Features:
 * - Stats cards: Total Proxies, Healthy, Avg Score, Avg Response Time
 * - Table: Host:Port, Protocol badge, Geo (flag + code), Success Rate,
 *   Avg Latency, Score (progress bar), Requests, Status badge
 * - Empty state with setup instructions
 * - Auto-refresh every 15s
 */

import { useQuery } from "@tanstack/react-query";
import type { ProxyInfo } from "../api/types";

/* ── Helpers ── */

function protocolBadgeClass(proto: string): string {
  switch (proto.toLowerCase()) {
    case "https":
      return "badge--completed";
    case "socks5":
      return "badge--running";
    case "socks4":
      return "badge--queued";
    default:
      return "badge--cancelled";
  }
}

function successRateColor(rate: number): string {
  if (rate >= 0.9) return "var(--color-success)";
  if (rate >= 0.7) return "var(--color-warning)";
  return "var(--color-error)";
}

function geoFlag(geoCode: string | null): string {
  if (!geoCode) return "🌐";
  // Convert ISO 3166-1 alpha-2 to flag emoji
  const code = geoCode.toUpperCase().slice(0, 2);
  if (code.length !== 2) return "🌐";
  return String.fromCodePoint(
    ...code.split("").map((c) => 0x1f1e6 + c.charCodeAt(0) - 65),
  );
}

/* ── Score mini bar ── */

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8
      ? "var(--color-success)"
      : score >= 0.5
      ? "var(--color-warning)"
      : "var(--color-error)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 90 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: "var(--color-border)",
          borderRadius: 99,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 99,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          color,
          minWidth: 32,
          textAlign: "right",
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

/* ── Skeleton row ── */

function SkeletonRow() {
  return (
    <tr>
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i}>
          <div
            style={{
              height: 14,
              background: "var(--color-border)",
              borderRadius: 4,
              opacity: 0.5,
              width: i === 0 ? 140 : i === 7 ? 70 : 80,
              animation: "pulse 1.4s ease-in-out infinite",
            }}
          />
        </td>
      ))}
    </tr>
  );
}

/* ── Component ── */

// Stub — the real hook will come from useRouting/useProxies when that agent delivers it.
// We use a generic useQuery placeholder so the page compiles independently.
function useProxyPool(options?: { refetchInterval?: number }) {
  return useQuery<ProxyInfo[]>({
    queryKey: ["proxies", "pool"],
    queryFn: async () => {
      const res = await fetch("/api/v1/proxies");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<ProxyInfo[]>;
    },
    refetchInterval: options?.refetchInterval,
  });
}

export function ProxyPage() {
  const { data, isLoading, error, refetch } = useProxyPool({
    refetchInterval: 15_000,
  });

  const proxies: ProxyInfo[] = data ?? [];

  // Aggregate stats
  const totalProxies = proxies.length;
  const healthyProxies = proxies.filter((p) => p.is_available).length;
  const avgScore =
    proxies.length > 0
      ? proxies.reduce((s, p) => s + p.score, 0) / proxies.length
      : 0;
  const avgResponseMs =
    proxies.length > 0
      ? proxies.reduce((s, p) => s + p.avg_response_time, 0) / proxies.length
      : 0;

  const stats = [
    {
      label: "Total Proxies",
      value: totalProxies,
      sub: "In pool",
    },
    {
      label: "Healthy",
      value: healthyProxies,
      sub: "Available for use",
      color: "var(--color-success)",
    },
    {
      label: "Avg Score",
      value: `${Math.round(avgScore * 100)}%`,
      sub: "Pool quality",
      color:
        avgScore >= 0.8
          ? "var(--color-success)"
          : avgScore >= 0.5
          ? "var(--color-warning)"
          : "var(--color-error)",
    },
    {
      label: "Avg Response",
      value:
        avgResponseMs > 0
          ? avgResponseMs >= 1000
            ? `${(avgResponseMs / 1000).toFixed(1)}s`
            : `${Math.round(avgResponseMs)}ms`
          : "—",
      sub: "Median latency",
    },
  ];

  return (
    <>
      <div className="page-header">
        <h2>Proxies</h2>
        <p>
          Monitor proxy pool health, success rates, and response times.
          Auto-refreshes every 15s.
        </p>
      </div>

      <div className="page-body">
        {/* Stats cards */}
        <div className="stats-grid">
          {stats.map((s) => (
            <div key={s.label} className="stat-card">
              <div className="stat-label">{s.label}</div>
              <div
                className="stat-value"
                style={s.color ? { color: s.color } : undefined}
              >
                {s.value}
              </div>
              <div className="stat-sub">{s.sub}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>
              {totalProxies} prox{totalProxies !== 1 ? "ies" : "y"}
            </h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              {isLoading ? "Refreshing…" : "Refresh"}
            </button>
          </div>

          {/* Error */}
          {error && !isLoading && (
            <div className="empty-state">
              <h3>Failed to load proxy pool</h3>
              <p>Check the control plane connection and try again.</p>
              <button
                className="btn btn-secondary"
                style={{ marginTop: 16 }}
                onClick={() => refetch()}
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty */}
          {!isLoading && !error && proxies.length === 0 && (
            <div className="empty-state">
              <h3>No proxies configured</h3>
              <p>
                Add proxies to your pool via the{" "}
                <code
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    background: "var(--color-bg)",
                    padding: "1px 5px",
                    borderRadius: 3,
                    border: "1px solid var(--color-border)",
                  }}
                >
                  PROXY_LIST
                </code>{" "}
                environment variable or the proxy management API. Proxies are
                used for the HTTP and browser execution lanes to avoid IP
                blocks.
              </p>
            </div>
          )}

          {/* Table */}
          {!error && (isLoading || proxies.length > 0) && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Host : Port</th>
                    <th>Protocol</th>
                    <th>Geo</th>
                    <th>Success Rate</th>
                    <th>Avg Latency</th>
                    <th>Score</th>
                    <th>Requests</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading && proxies.length === 0
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <SkeletonRow key={i} />
                      ))
                    : proxies.map((p) => (
                        <tr key={`${p.host}:${p.port}`}>
                          {/* Host:Port */}
                          <td>
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: 13,
                                fontWeight: 500,
                              }}
                            >
                              {p.host}
                              <span
                                style={{
                                  color: "var(--color-text-secondary)",
                                }}
                              >
                                :{p.port}
                              </span>
                            </span>
                          </td>

                          {/* Protocol */}
                          <td>
                            <span
                              className={`badge ${protocolBadgeClass(p.protocol)}`}
                              style={{ textTransform: "uppercase" }}
                            >
                              {p.protocol}
                            </span>
                          </td>

                          {/* Geo */}
                          <td>
                            <span
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                fontSize: 13,
                              }}
                            >
                              <span style={{ fontSize: 16 }}>
                                {geoFlag(p.geo)}
                              </span>
                              <span
                                style={{
                                  fontFamily: "var(--font-mono)",
                                  fontSize: 11,
                                  color: "var(--color-text-secondary)",
                                  fontWeight: 600,
                                  textTransform: "uppercase",
                                }}
                              >
                                {p.geo ?? "N/A"}
                              </span>
                            </span>
                          </td>

                          {/* Success Rate */}
                          <td>
                            <span
                              style={{
                                fontSize: 13,
                                fontWeight: 600,
                                color: successRateColor(p.success_rate),
                              }}
                            >
                              {(p.success_rate * 100).toFixed(1)}%
                            </span>
                          </td>

                          {/* Avg Latency */}
                          <td
                            style={{
                              fontSize: 13,
                              color: "var(--color-text-secondary)",
                              fontFamily: "var(--font-mono)",
                            }}
                          >
                            {p.avg_response_time >= 1000
                              ? `${(p.avg_response_time / 1000).toFixed(1)}s`
                              : `${Math.round(p.avg_response_time)}ms`}
                          </td>

                          {/* Score bar */}
                          <td>
                            <ScoreBar score={p.score} />
                          </td>

                          {/* Total requests */}
                          <td
                            style={{
                              fontSize: 13,
                              color: "var(--color-text-secondary)",
                              fontFamily: "var(--font-mono)",
                            }}
                          >
                            {p.total_requests.toLocaleString()}
                          </td>

                          {/* Status */}
                          <td>
                            <span
                              className={`badge ${
                                p.is_available
                                  ? "badge--completed"
                                  : "badge--timeout"
                              }`}
                            >
                              {p.is_available ? "Available" : "Cooldown"}
                            </span>
                          </td>
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
