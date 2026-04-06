/**
 * ExtractPage — Extract specific fields from any webpage using a schema.
 */

import { useState, type FormEvent } from "react";
import { extract } from "../api/client";

interface ExtractResult {
  confidence?: number;
  extraction_method?: string;
  data?: Record<string, unknown>;
  raw?: unknown;
  [key: string]: unknown;
}

const SCHEMA_PLACEHOLDER = `{
  "name": "string",
  "price": "number",
  "description": "string"
}`;

export function ExtractPage() {
  const [url, setUrl] = useState("");
  const [schema, setSchema] = useState("");
  const [outputFormat, setOutputFormat] = useState("json");
  const [isExtracting, setIsExtracting] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [error, setError] = useState("");

  async function handleExtract(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;

    setIsExtracting(true);
    setError("");
    setResult(null);

    let parsedSchema: Record<string, unknown> | undefined;
    if (schema.trim()) {
      try {
        parsedSchema = JSON.parse(schema.trim());
      } catch {
        setError("Invalid JSON schema. Please check the syntax.");
        setIsExtracting(false);
        return;
      }
    }

    try {
      const res = await extract.run({
        url: url.trim(),
        schema: parsedSchema,
        output_format: outputFormat,
      });
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Extraction failed";
      setError(msg);
    } finally {
      setIsExtracting(false);
    }
  }

  const extractedData = result?.data ?? result?.extracted_data as Record<string, unknown> | undefined ?? null;
  const confidence = result?.confidence;
  const method = result?.extraction_method;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: "linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", margin: 0 }}>Structured Extract</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Extract specific fields from any webpage using a schema
            </p>
          </div>
        </div>
      </div>

      {/* Info box */}
      <div style={{
        padding: "14px 18px",
        marginBottom: 20,
        borderRadius: 10,
        border: "1px solid var(--color-border)",
        background: "rgba(124, 58, 237, 0.05)",
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        fontSize: 13,
        color: "var(--color-text-secondary)",
        lineHeight: 1.5,
      }}>
        <span style={{ fontSize: 16, lineHeight: 1 }}>&#128196;</span>
        <div>
          <strong style={{ color: "var(--color-text)" }}>Structured Extract</strong> lets you define exactly which fields to extract using a JSON schema. The system scrapes the page and maps data to your schema fields.
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Use cases:</strong> Extract title+price+availability from product pages, pull author+date+content from articles
          </span>
          <br />
          <span style={{ fontSize: 12 }}>
            <strong>Limitation:</strong> Works best on pages with clear HTML structure
          </span>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleExtract} style={{ marginBottom: 24 }}>
        <div className="accent-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                URL
              </label>
              <input
                type="text"
                placeholder="https://example.com/product"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isExtracting}
                style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                Schema (JSON)
              </label>
              <textarea
                placeholder={SCHEMA_PLACEHOLDER}
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                disabled={isExtracting}
                rows={6}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: 13,
                  fontFamily: "monospace",
                  resize: "vertical",
                  boxSizing: "border-box",
                  lineHeight: 1.5,
                }}
              />
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ minWidth: 140 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                  Output Format
                </label>
                <select
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  disabled={isExtracting}
                  style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", fontSize: 14, cursor: "pointer", boxSizing: "border-box" }}
                >
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                </select>
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isExtracting || !url.trim()}
                style={{ height: 44, paddingInline: 28 }}
              >
                {isExtracting ? (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span className="spinner" /> Extracting...
                  </span>
                ) : "Extract"}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && <div className="form-error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Loading */}
      {isExtracting && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
          <p style={{ color: "var(--color-text-secondary)" }}>Extracting data from page...</p>
        </div>
      )}

      {/* Results */}
      {!isExtracting && result && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--color-text)", marginBottom: 12 }}>Extraction Results</h3>

          {/* Badges */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
            {confidence != null && (
              <span style={{
                display: "inline-block",
                padding: "4px 12px",
                borderRadius: 9999,
                fontSize: 13,
                fontWeight: 600,
                color: "white",
                background: confidence >= 0.8 ? "#059669" : confidence >= 0.5 ? "#d97706" : "#dc2626",
              }}>
                Confidence: {Math.round(confidence * 100)}%
              </span>
            )}
            {method && (
              <span style={{
                display: "inline-block",
                padding: "4px 12px",
                borderRadius: 9999,
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
              }}>
                Method: {method}
              </span>
            )}
          </div>

          {/* Key-value table */}
          {extractedData && Object.keys(extractedData).length > 0 && (
            <div className="accent-card" style={{ padding: 0, marginBottom: 16, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--color-surface)" }}>
                    <th style={{ textAlign: "left", padding: "10px 16px", fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid var(--color-border)" }}>Field</th>
                    <th style={{ textAlign: "left", padding: "10px 16px", fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid var(--color-border)" }}>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(extractedData).map(([key, value]) => (
                    <tr key={key}>
                      <td style={{ padding: "10px 16px", fontSize: 13, fontWeight: 600, color: "var(--color-text)", borderBottom: "1px solid var(--color-border)", whiteSpace: "nowrap" }}>{key}</td>
                      <td style={{ padding: "10px 16px", fontSize: 13, color: "var(--color-text)", borderBottom: "1px solid var(--color-border)", wordBreak: "break-word" }}>
                        {typeof value === "object" ? JSON.stringify(value) : String(value ?? "")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Raw JSON */}
          <div className="accent-card" style={{ padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>Raw JSON</div>
            <pre style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              overflow: "auto",
              maxHeight: 400,
              fontSize: 12,
              lineHeight: 1.5,
              color: "var(--color-text)",
              margin: 0,
            }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isExtracting && !result && !error && (
        <div className="accent-card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: "linear-gradient(135deg, #7c3aed, #a78bfa)",
            display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>Extract structured data from any page</h3>
          <p style={{ color: "var(--color-text-secondary)", maxWidth: 400, margin: "0 auto" }}>
            Enter a URL and define a JSON schema to extract specific fields from the webpage.
          </p>
        </div>
      )}
    </div>
  );
}

export default ExtractPage;
