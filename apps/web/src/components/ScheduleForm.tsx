/**
 * ScheduleForm — Modal form for creating a new scheduled task.
 * Supports cron expressions and interval shortcut buttons.
 * Submits a ScheduleCreateRequest object.
 */

import { useState, useEffect, useCallback } from "react";
import type { ScheduleCreateRequest } from "../api/types";

interface ScheduleFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (req: ScheduleCreateRequest) => void;
}

type ScheduleType = "cron" | "interval";

const INTERVAL_SHORTCUTS: { label: string; cron: string }[] = [
  { label: "Every 5m",  cron: "*/5 * * * *" },
  { label: "Every 15m", cron: "*/15 * * * *" },
  { label: "Every 1h",  cron: "0 * * * *" },
  { label: "Every 6h",  cron: "0 */6 * * *" },
  { label: "Every 24h", cron: "0 0 * * *" },
];

const PRIORITY_LABELS: Record<number, string> = {
  1: "Low",
  2: "Below Normal",
  3: "Normal",
  4: "Above Normal",
  5: "High",
};

export function ScheduleForm({ open, onClose, onSubmit }: ScheduleFormProps) {
  const [url, setUrl]                   = useState("");
  const [scheduleType, setScheduleType] = useState<ScheduleType>("cron");
  const [cronExpr, setCronExpr]         = useState("*/30 * * * *");
  const [priority, setPriority]         = useState(3);
  const [enabled, setEnabled]           = useState(true);
  const [urlError, setUrlError]         = useState<string | null>(null);
  const [cronError, setCronError]       = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setUrl("");
    setScheduleType("cron");
    setCronExpr("*/30 * * * *");
    setPriority(3);
    setEnabled(true);
    setUrlError(null);
    setCronError(null);
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [open, handleKeyDown]);

  useEffect(() => {
    if (!open) resetForm();
  }, [open, resetForm]);

  if (!open) return null;

  function validate(): boolean {
    let valid = true;
    if (!url.trim()) {
      setUrlError("URL is required");
      valid = false;
    } else {
      try {
        new URL(url.trim());
        setUrlError(null);
      } catch {
        setUrlError("Enter a valid URL (e.g. https://example.com)");
        valid = false;
      }
    }
    if (!cronExpr.trim()) {
      setCronError("Schedule expression is required");
      valid = false;
    } else {
      setCronError(null);
    }
    return valid;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    const req: ScheduleCreateRequest = {
      url: url.trim(),
      schedule: cronExpr.trim(),
      priority,
      metadata: { enabled, schedule_type: scheduleType },
    };
    onSubmit(req);
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content">
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <h3
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: "var(--color-text)",
              letterSpacing: "-0.01em",
            }}
          >
            New Scheduled Task
          </h3>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            style={{ padding: "4px 8px", lineHeight: 1 }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* URL */}
          <div className="form-group">
            <label htmlFor="sf-url">Target URL</label>
            <input
              id="sf-url"
              type="url"
              className={`form-input${urlError ? " form-input--error" : ""}`}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/data"
              autoFocus
            />
            {urlError && <span className="form-error">{urlError}</span>}
          </div>

          {/* Schedule type */}
          <div className="form-group">
            <label>Schedule Type</label>
            <div style={{ display: "flex", gap: 8 }}>
              {(["cron", "interval"] as ScheduleType[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`btn btn-sm ${scheduleType === t ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setScheduleType(t)}
                  style={{ textTransform: "capitalize" }}
                >
                  {t === "cron" ? "Cron Expression" : "Quick Interval"}
                </button>
              ))}
            </div>
          </div>

          {/* Cron expression */}
          {scheduleType === "cron" && (
            <div className="form-group">
              <label htmlFor="sf-cron">Cron Expression</label>
              <input
                id="sf-cron"
                type="text"
                className={`form-input${cronError ? " form-input--error" : ""}`}
                value={cronExpr}
                onChange={(e) => setCronExpr(e.target.value)}
                placeholder="*/30 * * * *"
                style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
              />
              {cronError && <span className="form-error">{cronError}</span>}
              <span className="form-hint">
                Format: minute hour day-of-month month day-of-week
              </span>
            </div>
          )}

          {/* Interval shortcuts */}
          {scheduleType === "interval" && (
            <div className="form-group">
              <label>Quick Interval</label>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {INTERVAL_SHORTCUTS.map((s) => (
                  <button
                    key={s.cron}
                    type="button"
                    className={`btn btn-sm ${cronExpr === s.cron ? "btn-primary" : "btn-secondary"}`}
                    onClick={() => setCronExpr(s.cron)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <div
                style={{
                  marginTop: 8,
                  padding: "6px 10px",
                  background: "var(--color-bg)",
                  borderRadius: "var(--radius-sm)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  color: "var(--color-text-secondary)",
                }}
              >
                {cronExpr}
              </div>
            </div>
          )}

          {/* Priority slider */}
          <div className="form-group">
            <label htmlFor="sf-priority">
              Priority —{" "}
              <span style={{ color: "var(--color-primary)", fontWeight: 600 }}>
                {PRIORITY_LABELS[priority] ?? priority}
              </span>
            </label>
            <input
              id="sf-priority"
              type="range"
              className="form-range"
              min={1}
              max={5}
              step={1}
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
            <div className="form-range-labels">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>

          {/* Enabled toggle */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 12px",
              background: "var(--color-bg)",
              borderRadius: "var(--radius-md)",
              marginBottom: 16,
              border: "1px solid var(--color-border)",
            }}
          >
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Enable on creation</div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                Schedule will begin running immediately
              </div>
            </div>
            <label
              style={{
                position: "relative",
                display: "inline-block",
                width: 40,
                height: 22,
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                style={{ opacity: 0, width: 0, height: 0, position: "absolute" }}
              />
              <span
                style={{
                  position: "absolute",
                  inset: 0,
                  background: enabled ? "var(--color-primary)" : "var(--color-border)",
                  borderRadius: 9999,
                  transition: "background 0.2s",
                }}
              />
              <span
                style={{
                  position: "absolute",
                  top: 3,
                  left: enabled ? 21 : 3,
                  width: 16,
                  height: 16,
                  background: "#ffffff",
                  borderRadius: "50%",
                  transition: "left 0.2s",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                }}
              />
            </label>
          </div>

          {/* Actions */}
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Create Schedule
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
