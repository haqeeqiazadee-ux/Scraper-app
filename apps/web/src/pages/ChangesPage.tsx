/**
 * ChangesPage — Client-side JSON snapshot comparison for change detection.
 * Compares two JSON arrays to detect added, removed, price changes, and field changes.
 */

import { useState } from "react";

interface ChangeItem {
  type: "added" | "removed" | "price_change" | "field_change";
  key: string;
  fields: string[];
  oldValue: string;
  newValue: string;
  priceDelta: string;
}

interface Summary {
  added: number;
  removed: number;
  priceChanges: number;
  fieldChanges: number;
}

const IGNORED_FIELDS = ["_relevance_score", "_confidence", "extracted_at"];

function getItemKey(item: Record<string, unknown>): string {
  return (item.product_url as string) || (item.name as string) || JSON.stringify(item).slice(0, 60);
}

function compareSnapshots(
  oldItems: Record<string, unknown>[],
  newItems: Record<string, unknown>[],
  priceThreshold: number,
): { changes: ChangeItem[]; summary: Summary } {
  const changes: ChangeItem[] = [];
  const summary: Summary = { added: 0, removed: 0, priceChanges: 0, fieldChanges: 0 };

  const oldMap = new Map<string, Record<string, unknown>>();
  for (const item of oldItems) {
    oldMap.set(getItemKey(item), item);
  }
  const newMap = new Map<string, Record<string, unknown>>();
  for (const item of newItems) {
    newMap.set(getItemKey(item), item);
  }

  // Detect removed items
  for (const [key] of oldMap) {
    if (!newMap.has(key)) {
      summary.removed++;
      changes.push({ type: "removed", key, fields: [], oldValue: "", newValue: "", priceDelta: "" });
    }
  }

  // Detect added items
  for (const [key] of newMap) {
    if (!oldMap.has(key)) {
      summary.added++;
      changes.push({ type: "added", key, fields: [], oldValue: "", newValue: "", priceDelta: "" });
    }
  }

  // Detect changes in matched items
  for (const [key, newItem] of newMap) {
    const oldItem = oldMap.get(key);
    if (!oldItem) continue;

    const allFields = new Set([...Object.keys(oldItem), ...Object.keys(newItem)]);
    const changedFields: string[] = [];
    let hasPriceChange = false;
    let priceDelta = "";
    let priceOld = "";
    let priceNew = "";

    for (const field of allFields) {
      if (IGNORED_FIELDS.includes(field)) continue;
      const oldVal = JSON.stringify(oldItem[field] ?? "");
      const newVal = JSON.stringify(newItem[field] ?? "");
      if (oldVal !== newVal) {
        changedFields.push(field);

        if (field === "price" || field === "current_price") {
          const oldPrice = parseFloat(String(oldItem[field] ?? 0));
          const newPrice = parseFloat(String(newItem[field] ?? 0));
          if (!isNaN(oldPrice) && !isNaN(newPrice) && oldPrice > 0) {
            const pctChange = ((newPrice - oldPrice) / oldPrice) * 100;
            if (Math.abs(pctChange) >= priceThreshold) {
              hasPriceChange = true;
              priceOld = `$${oldPrice.toFixed(2)}`;
              priceNew = `$${newPrice.toFixed(2)}`;
              const sign = pctChange > 0 ? "+" : "";
              priceDelta = `${priceOld} \u2192 ${priceNew} (${sign}${pctChange.toFixed(1)}%)`;
            }
          }
        }
      }
    }

    if (hasPriceChange) {
      summary.priceChanges++;
      changes.push({
        type: "price_change",
        key,
        fields: changedFields,
        oldValue: priceOld,
        newValue: priceNew,
        priceDelta,
      });
    } else if (changedFields.length > 0) {
      summary.fieldChanges++;
      const oldVals = changedFields.map((f) => String(oldItem[f] ?? "")).join(", ");
      const newVals = changedFields.map((f) => String(newItem[f] ?? "")).join(", ");
      changes.push({
        type: "field_change",
        key,
        fields: changedFields,
        oldValue: oldVals,
        newValue: newVals,
        priceDelta: "",
      });
    }
  }

  return { changes, summary };
}

const BADGE_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  added: { bg: "#dcfce7", color: "#166534", label: "Added" },
  removed: { bg: "#fee2e2", color: "#991b1b", label: "Removed" },
  price_change: { bg: "#fff7ed", color: "#9a3412", label: "Price Change" },
  field_change: { bg: "#dbeafe", color: "#1e40af", label: "Field Change" },
};

export function ChangesPage() {
  const [oldSnapshot, setOldSnapshot] = useState("");
  const [newSnapshot, setNewSnapshot] = useState("");
  const [threshold, setThreshold] = useState(10);
  const [changes, setChanges] = useState<ChangeItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [hasCompared, setHasCompared] = useState(false);

  function handleCompare() {
    setError("");
    setHasCompared(true);

    let oldArr: Record<string, unknown>[];
    let newArr: Record<string, unknown>[];

    try {
      oldArr = JSON.parse(oldSnapshot);
      if (!Array.isArray(oldArr)) throw new Error("Old snapshot must be a JSON array");
    } catch {
      setError("Failed to parse Old Snapshot. Please provide a valid JSON array.");
      setChanges([]);
      setSummary(null);
      return;
    }

    try {
      newArr = JSON.parse(newSnapshot);
      if (!Array.isArray(newArr)) throw new Error("New snapshot must be a JSON array");
    } catch {
      setError("Failed to parse New Snapshot. Please provide a valid JSON array.");
      setChanges([]);
      setSummary(null);
      return;
    }

    const result = compareSnapshots(oldArr, newArr, threshold);
    setChanges(result.changes);
    setSummary(result.summary);
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #f97316 0%, #fdba74 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v14" />
              <path d="M5 10l7 7 7-7" />
              <path d="M5 21h14" />
              <path d="M18 3v6" />
              <path d="M15 3h6" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>Change Detection</h1>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Compare data snapshots to detect price changes, new items, and modifications
            </p>
          </div>
        </div>
      </div>

      {/* Two-panel form */}
      <div className="accent-card" style={{ marginBottom: 24, padding: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              Old Snapshot
            </label>
            <textarea
              value={oldSnapshot}
              onChange={(e) => setOldSnapshot(e.target.value)}
              placeholder='Paste JSON array of items...'
              rows={12}
              style={{
                width: "100%",
                fontFamily: "monospace",
                fontSize: 13,
                padding: 12,
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                color: "var(--color-text)",
                resize: "vertical",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
              New Snapshot
            </label>
            <textarea
              value={newSnapshot}
              onChange={(e) => setNewSnapshot(e.target.value)}
              placeholder='Paste JSON array of items...'
              rows={12}
              style={{
                width: "100%",
                fontFamily: "monospace",
                fontSize: 13,
                padding: 12,
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                color: "var(--color-text)",
                resize: "vertical",
                boxSizing: "border-box",
              }}
            />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, flexWrap: "wrap" }}>
          <label style={{ fontSize: 13, color: "var(--color-text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
            Alert when price changes exceed
            <input
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              min={0}
              max={100}
              style={{
                width: 60,
                padding: "6px 8px",
                borderRadius: 6,
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                color: "var(--color-text)",
                fontSize: 13,
                textAlign: "center",
              }}
            />
            %
          </label>
          <button
            type="button"
            className="btn btn-primary btn-lg"
            onClick={handleCompare}
            disabled={!oldSnapshot.trim() || !newSnapshot.trim()}
            style={{ height: 44, paddingInline: 40 }}
          >
            Compare
          </button>
        </div>
      </div>

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Summary cards */}
      {summary && !error && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
          <SummaryCard label="Added" count={summary.added} bg="#dcfce7" color="#166534" />
          <SummaryCard label="Removed" count={summary.removed} bg="#fee2e2" color="#991b1b" />
          <SummaryCard label="Price Changes" count={summary.priceChanges} bg="#fff7ed" color="#9a3412" />
          <SummaryCard label="Field Changes" count={summary.fieldChanges} bg="#dbeafe" color="#1e40af" />
        </div>
      )}

      {/* Changes table */}
      {hasCompared && !error && changes.length > 0 && (
        <div style={{ border: "1px solid var(--color-border)", borderRadius: 12, overflow: "hidden", background: "var(--color-surface)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--color-bg)", borderBottom: "1px solid var(--color-border)" }}>
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Type</th>
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Item</th>
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Changed Fields</th>
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Old Value</th>
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>New Value</th>
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--color-text-secondary)" }}>Price Delta</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((change, i) => {
                const badge = BADGE_STYLES[change.type];
                return (
                  <tr key={i} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        background: badge.bg,
                        color: badge.color,
                      }}>
                        {badge.label}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--color-text)", maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {change.key}
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--color-text-secondary)" }}>
                      {change.fields.length > 0 ? change.fields.join(", ") : "\u2014"}
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--color-text-secondary)", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {change.oldValue || "\u2014"}
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--color-text-secondary)", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {change.newValue || "\u2014"}
                    </td>
                    <td style={{ padding: "10px 16px", fontWeight: 600, color: change.type === "price_change" ? "#9a3412" : "var(--color-text-secondary)" }}>
                      {change.priceDelta || "\u2014"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state after compare */}
      {hasCompared && !error && changes.length === 0 && summary && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>&#x2714;</div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>No Changes Detected</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            The two snapshots are identical. No added, removed, or modified items found.
          </p>
        </div>
      )}

      {/* Initial empty state */}
      {!hasCompared && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #f97316, #fdba74)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v14" />
              <path d="M5 10l7 7 7-7" />
              <path d="M5 21h14" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Paste two JSON snapshots to compare</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Paste old and new JSON arrays above to detect added items, removed items, price changes, and field modifications.
          </p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, count, bg, color }: { label: string; count: number; bg: string; color: string }) {
  return (
    <div className="accent-card" style={{ textAlign: "center" }}>
      <div style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        background: bg,
        color,
        marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color, marginBottom: 2 }}>{count}</div>
    </div>
  );
}

export default ChangesPage;
