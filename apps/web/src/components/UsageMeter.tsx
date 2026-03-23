/**
 * UsageMeter — Horizontal progress bar showing resource utilization.
 * Turns amber at 80%, red at 95%. Smooth CSS transition on width.
 */

interface UsageMeterProps {
  label: string;
  current: number;
  max: number;
  unit?: string;
  warningThreshold?: number;
}

function formatValue(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function getBarColor(ratio: number): string {
  if (ratio >= 0.95) return "var(--color-error)";
  if (ratio >= 0.8) return "var(--color-warning)";
  return "var(--color-primary)";
}

function getBarGradient(ratio: number): string {
  if (ratio >= 0.95)
    return "linear-gradient(90deg, #dc2626 0%, #ef4444 100%)";
  if (ratio >= 0.8)
    return "linear-gradient(90deg, #d97706 0%, #f59e0b 100%)";
  return "linear-gradient(90deg, #2563eb 0%, #3b82f6 100%)";
}

export function UsageMeter({
  label,
  current,
  max,
  unit,
  warningThreshold = 0.8,
}: UsageMeterProps) {
  const ratio = max > 0 ? Math.min(current / max, 1) : 0;
  const pct = Math.round(ratio * 100);
  const barColor = getBarColor(ratio);
  const barGradient = getBarGradient(ratio);
  const isWarning = ratio >= warningThreshold && ratio < 0.95;
  const isCritical = ratio >= 0.95;

  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        padding: "12px 16px",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
        }}
      >
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--color-text)",
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: barColor,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {formatValue(current)} / {formatValue(max)}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>

      {/* Progress track */}
      <div
        style={{
          height: 6,
          background: "var(--color-bg)",
          borderRadius: 9999,
          overflow: "hidden",
          border: "1px solid var(--color-border)",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: barGradient,
            borderRadius: 9999,
            transition: "width 0.4s ease, background 0.3s ease",
          }}
        />
      </div>

      {/* Footer hint */}
      {(isWarning || isCritical) && (
        <div
          style={{
            marginTop: 6,
            fontSize: 11,
            color: barColor,
            fontWeight: 500,
          }}
        >
          {isCritical
            ? `Critical — ${pct}% used`
            : `${pct}% used — approaching limit`}
        </div>
      )}
    </div>
  );
}
