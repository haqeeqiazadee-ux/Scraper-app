/**
 * AnalyticsCards — Two-row analytics grid.
 * Row 1: 4 stat cards (Total Tasks, Success Rate, Avg Duration, Tasks Today).
 * Row 2: Lane Distribution (stacked bar) + Top Domains (mini list).
 * Pure CSS — no charting library.
 */

import type { AnalyticsData } from "../api/types";

interface AnalyticsCardsProps {
  data: AnalyticsData;
}

/* ── Helpers ── */

function formatDuration(ms: number): string {
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function formatPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

/* ── Lane colors ── */

const LANE_COLORS: Record<string, string> = {
  http: "#2563eb",
  browser: "#7c3aed",
  hard_target: "#dc2626",
  api: "#059669",
};

function laneColor(lane: string): string {
  return LANE_COLORS[lane.toLowerCase()] ?? "#6b7280";
}

/* ── Stat card ── */

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  trend?: "up" | "down" | "neutral";
}

function StatCard({ label, value, sub, trend }: StatCardProps) {
  const trendSymbol =
    trend === "up" ? "↑" : trend === "down" ? "↓" : null;
  const trendColor =
    trend === "up"
      ? "var(--color-success)"
      : trend === "down"
        ? "var(--color-error)"
        : "var(--color-text-secondary)";

  return (
    <div
      className="stat-card"
      style={{ position: "relative", overflow: "hidden" }}
    >
      {/* Subtle top accent line */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: "linear-gradient(90deg, var(--color-primary) 0%, transparent 100%)",
          opacity: 0.4,
        }}
      />
      <div className="stat-label">{label}</div>
      <div
        className="stat-value"
        style={{ display: "flex", alignItems: "baseline", gap: 6 }}
      >
        {value}
        {trendSymbol && (
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: trendColor,
              lineHeight: 1,
            }}
          >
            {trendSymbol}
          </span>
        )}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

/* ── Lane Distribution bar ── */

function LaneDistributionBar({
  distribution,
}: {
  distribution: Record<string, number>;
}) {
  const total = Object.values(distribution).reduce((s, v) => s + v, 0);
  const lanes = Object.entries(distribution).sort((a, b) => b[1] - a[1]);

  if (total === 0) {
    return (
      <div
        style={{
          fontSize: 13,
          color: "var(--color-text-secondary)",
          textAlign: "center",
          padding: "12px 0",
        }}
      >
        No data yet
      </div>
    );
  }

  return (
    <div>
      {/* Stacked bar */}
      <div
        style={{
          display: "flex",
          height: 12,
          borderRadius: 9999,
          overflow: "hidden",
          gap: 1,
          marginBottom: 10,
        }}
      >
        {lanes.map(([lane, count]) => {
          const pct = (count / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={lane}
              title={`${lane}: ${count} (${pct.toFixed(1)}%)`}
              style={{
                width: `${pct}%`,
                background: laneColor(lane),
                transition: "width 0.4s ease",
                flexShrink: 0,
              }}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "6px 14px",
        }}
      >
        {lanes.map(([lane, count]) => (
          <div
            key={lane}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              fontSize: 12,
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: laneColor(lane),
                flexShrink: 0,
              }}
            />
            <span style={{ color: "var(--color-text-secondary)", textTransform: "capitalize" }}>
              {lane.replace("_", "-")}
            </span>
            <span style={{ fontWeight: 600, color: "var(--color-text)" }}>
              {count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Top Domains list ── */

function TopDomainsList({
  domains,
}: {
  domains: { domain: string; count: number }[];
}) {
  if (domains.length === 0) {
    return (
      <div
        style={{
          fontSize: 13,
          color: "var(--color-text-secondary)",
          textAlign: "center",
          padding: "12px 0",
        }}
      >
        No data yet
      </div>
    );
  }

  const maxCount = Math.max(...domains.map((d) => d.count), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {domains.slice(0, 6).map((d) => (
        <div
          key={d.domain}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          {/* Mini bar */}
          <div
            style={{
              flex: 1,
              height: 4,
              background: "var(--color-border)",
              borderRadius: 9999,
              overflow: "hidden",
              minWidth: 0,
              position: "relative",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                width: `${(d.count / maxCount) * 100}%`,
                background: "var(--color-primary)",
                borderRadius: 9999,
                transition: "width 0.4s ease",
                opacity: 0.7,
              }}
            />
          </div>
          {/* Domain name */}
          <span
            style={{
              fontSize: 12,
              color: "var(--color-text)",
              fontFamily: "var(--font-mono)",
              width: 140,
              flexShrink: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              textAlign: "right",
            }}
            title={d.domain}
          >
            {d.domain}
          </span>
          {/* Count */}
          <span
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              width: 32,
              textAlign: "right",
              flexShrink: 0,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {d.count}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Main component ── */

export function AnalyticsCards({ data }: AnalyticsCardsProps) {
  const successRatePct = data.success_rate * 100;
  const successTrend: "up" | "down" | "neutral" =
    successRatePct >= 90 ? "up" : successRatePct < 70 ? "down" : "neutral";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Row 1 — Stat cards */}
      <div className="stats-grid">
        <StatCard
          label="Total Tasks"
          value={data.total_tasks.toLocaleString()}
          sub={`${data.completed_tasks} completed`}
        />
        <StatCard
          label="Success Rate"
          value={formatPct(data.success_rate)}
          sub={`${data.failed_tasks} failed`}
          trend={successTrend}
        />
        <StatCard
          label="Avg Duration"
          value={formatDuration(data.avg_duration_ms)}
          sub="per task run"
        />
        <StatCard
          label="Tasks Today"
          value={data.tasks_today.toLocaleString()}
          sub="in current period"
          trend={data.tasks_today > 0 ? "up" : "neutral"}
        />
      </div>

      {/* Row 2 — Lane distribution + Top domains */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {/* Lane distribution */}
        <div className="card">
          <div className="card-header">
            <h3>Lane Distribution</h3>
            <span
              style={{
                fontSize: 12,
                color: "var(--color-text-secondary)",
              }}
            >
              {Object.values(data.lane_distribution).reduce((s, v) => s + v, 0)} runs
            </span>
          </div>
          <LaneDistributionBar distribution={data.lane_distribution} />
        </div>

        {/* Top domains */}
        <div className="card">
          <div className="card-header">
            <h3>Top Domains</h3>
            <span
              style={{
                fontSize: 12,
                color: "var(--color-text-secondary)",
              }}
            >
              by run count
            </span>
          </div>
          <TopDomainsList domains={data.top_domains} />
        </div>
      </div>
    </div>
  );
}
