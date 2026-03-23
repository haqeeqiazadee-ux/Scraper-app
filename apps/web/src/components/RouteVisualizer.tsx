/**
 * RouteVisualizer — Visual display of a RouteDecision.
 * Shows selected lane as a highlighted card with icon + reason,
 * a confidence bar, and a fallback chain with arrow connectors.
 */

import type { RouteDecision } from "../api/types";

interface RouteVisualizerProps {
  decision: RouteDecision;
}

type Lane = string;

const LANE_META: Record<
  string,
  { label: string; icon: string; color: string; bg: string }
> = {
  http: {
    label: "HTTP",
    icon: "🌐",
    color: "#2563eb",
    bg: "rgba(37, 99, 235, 0.08)",
  },
  browser: {
    label: "Browser",
    icon: "🪟",
    color: "#7c3aed",
    bg: "rgba(124, 58, 237, 0.08)",
  },
  hard_target: {
    label: "Hard-Target",
    icon: "🛡",
    color: "#dc2626",
    bg: "rgba(220, 38, 38, 0.08)",
  },
  api: {
    label: "API",
    icon: "🔌",
    color: "#059669",
    bg: "rgba(5, 150, 105, 0.08)",
  },
};


function getLaneMeta(lane: Lane) {
  return (
    LANE_META[lane.toLowerCase()] ?? {
      label: lane,
      icon: "⚡",
      color: "var(--color-text)",
      bg: "var(--color-bg)",
    }
  );
}

function LaneChip({
  lane,
  active,
}: {
  lane: Lane;
  active?: boolean;
}) {
  const meta = getLaneMeta(lane);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        padding: "10px 14px",
        borderRadius: "var(--radius-md)",
        background: active ? meta.bg : "var(--color-bg)",
        border: `1.5px solid ${active ? meta.color : "var(--color-border)"}`,
        minWidth: 80,
        transition: "border-color 0.15s",
        opacity: active ? 1 : 0.65,
      }}
    >
      <span style={{ fontSize: 20, lineHeight: 1 }}>{meta.icon}</span>
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: active ? meta.color : "var(--color-text-secondary)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          whiteSpace: "nowrap",
        }}
      >
        {meta.label}
      </span>
    </div>
  );
}

function Arrow() {
  return (
    <span
      style={{
        fontSize: 16,
        color: "var(--color-text-secondary)",
        flexShrink: 0,
        lineHeight: 1,
        paddingTop: 14,
      }}
    >
      →
    </span>
  );
}

export function RouteVisualizer({ decision }: RouteVisualizerProps) {
  const meta = getLaneMeta(decision.lane);
  const confPct = Math.round(decision.confidence * 100);

  function confColor(): string {
    if (decision.confidence >= 0.8) return "var(--color-success)";
    if (decision.confidence >= 0.5) return "var(--color-warning)";
    return "var(--color-error)";
  }

  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: 20,
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Selected lane card */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 14,
          padding: "14px 16px",
          background: meta.bg,
          border: `1.5px solid ${meta.color}`,
          borderRadius: "var(--radius-md)",
          marginBottom: 16,
        }}
      >
        <span style={{ fontSize: 28, lineHeight: 1, flexShrink: 0 }}>
          {meta.icon}
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: meta.color,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              {meta.label}
            </span>
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 9999,
                background: "var(--color-surface)",
                color: meta.color,
                border: `1px solid ${meta.color}`,
              }}
            >
              Selected
            </span>
          </div>
          {decision.reason && (
            <div
              style={{
                fontSize: 13,
                color: "var(--color-text-secondary)",
                marginTop: 4,
                lineHeight: 1.5,
              }}
            >
              {decision.reason}
            </div>
          )}
        </div>
      </div>

      {/* Confidence bar */}
      <div style={{ marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 12,
            fontWeight: 600,
            marginBottom: 6,
          }}
        >
          <span style={{ color: "var(--color-text-secondary)" }}>Confidence</span>
          <span style={{ color: confColor() }}>{confPct}%</span>
        </div>
        <div
          style={{
            height: 4,
            background: "var(--color-bg)",
            borderRadius: 9999,
            overflow: "hidden",
            border: "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${confPct}%`,
              background: confColor(),
              borderRadius: 9999,
              transition: "width 0.4s ease",
            }}
          />
        </div>
      </div>

      {/* Fallback chain */}
      {decision.fallback_lanes.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 10,
            }}
          >
            Fallback Chain
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 6,
              flexWrap: "wrap",
            }}
          >
            <LaneChip lane={decision.lane} active />
            {decision.fallback_lanes.map((lane, i) => (
              <>
                <Arrow key={`arrow-${i}`} />
                <LaneChip key={lane} lane={lane} />
              </>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
