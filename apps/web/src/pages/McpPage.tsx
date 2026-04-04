/**
 * McpPage — Informational page for MCP Server setup and available tools.
 * No API calls; purely displays configuration and documentation.
 */

import { useState } from "react";

const TOOLS = [
  {
    name: "scrape",
    description: "Extract data from a single URL",
    params: ["url", "output_format"],
  },
  {
    name: "crawl",
    description: "Recursively crawl a website",
    params: ["url", "max_depth", "max_pages"],
  },
  {
    name: "search",
    description: "Search the web and scrape results",
    params: ["query", "max_results"],
  },
  {
    name: "extract",
    description: "Structured extraction with JSON schema",
    params: ["url", "schema"],
  },
  {
    name: "route",
    description: "Dry-run routing decision",
    params: ["url"],
  },
];

const CLAUDE_DESKTOP_CONFIG = `{
  "mcpServers": {
    "scraper-platform": {
      "command": "python",
      "args": ["-m", "packages.core.mcp_server"],
      "env": { "SCRAPER_API_KEY": "your-api-key" }
    }
  }
}`;

const VSCODE_CONFIG = `{
  "mcp": {
    "servers": {
      "scraper-platform": {
        "command": "python",
        "args": ["-m", "packages.core.mcp_server"]
      }
    }
  }
}`;

const START_COMMAND = "python -m packages.core.mcp_server";

const MCP_JSON_CONFIG = `{
  "mcpServers": {
    "scraper-platform": {
      "command": "python",
      "args": ["-m", "packages.core.mcp_server"]
    }
  }
}`;

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      style={{
        position: "absolute",
        top: 8,
        right: 8,
        padding: "4px 10px",
        fontSize: 11,
        fontWeight: 600,
        borderRadius: 4,
        border: "1px solid rgba(255,255,255,0.2)",
        background: copied ? "#22c55e" : "rgba(255,255,255,0.1)",
        color: "#fff",
        cursor: "pointer",
        transition: "all 0.15s",
      }}
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div style={{ position: "relative" }}>
      <CopyButton text={code} />
      <pre style={{
        fontFamily: "monospace",
        fontSize: 13,
        background: "#1e1e2e",
        color: "#cdd6f4",
        padding: 16,
        borderRadius: 8,
        overflowX: "auto",
        margin: 0,
        lineHeight: 1.5,
      }}>
        {code}
      </pre>
    </div>
  );
}

export function McpPage() {
  const [activeTab, setActiveTab] = useState<"claude" | "vscode">("claude");

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #22c55e 0%, #86efac 100%)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v6" />
              <path d="M12 18v4" />
              <path d="M4.93 4.93l4.24 4.24" />
              <path d="M14.83 14.83l4.24 4.24" />
              <path d="M2 12h6" />
              <path d="M18 12h4" />
              <path d="M4.93 19.07l4.24-4.24" />
              <path d="M14.83 9.17l4.24-4.24" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>MCP Server</h1>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
              Connect AI agents to your scraping platform via Model Context Protocol
            </p>
          </div>
        </div>
      </div>

      {/* Quick Start */}
      <div style={{
        border: "1px solid var(--color-border)",
        borderRadius: 12,
        padding: 24,
        background: "var(--color-surface)",
        marginBottom: 32,
      }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 20 }}>Quick Start</h2>

        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>
            1. Start the MCP server:
          </div>
          <CodeBlock code={START_COMMAND} />
        </div>

        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 8 }}>
            2. Or add to your MCP config:
          </div>
          <CodeBlock code={MCP_JSON_CONFIG} />
        </div>
      </div>

      {/* Available Tools */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 16 }}>Available Tools</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
          {TOOLS.map((tool) => (
            <div
              key={tool.name}
              style={{
                border: "1px solid var(--color-border)",
                borderRadius: 12,
                padding: 20,
                background: "var(--color-surface)",
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--color-text)", marginBottom: 6 }}>
                {tool.name}
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12, lineHeight: 1.4 }}>
                {tool.description}
              </div>
              <pre style={{
                fontFamily: "monospace",
                fontSize: 11,
                background: "#1e1e2e",
                color: "#cdd6f4",
                padding: 10,
                borderRadius: 6,
                margin: 0,
                lineHeight: 1.5,
              }}>
                {tool.params.map((p) => `  ${p}`).join("\n")}
              </pre>
            </div>
          ))}
        </div>
      </div>

      {/* Connection Config */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 16 }}>Connection Config</h2>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 0, marginBottom: 0 }}>
          <button
            type="button"
            onClick={() => setActiveTab("claude")}
            style={{
              padding: "10px 20px",
              fontSize: 13,
              fontWeight: 600,
              border: "1px solid var(--color-border)",
              borderBottom: activeTab === "claude" ? "1px solid var(--color-surface)" : "1px solid var(--color-border)",
              borderRadius: "8px 8px 0 0",
              background: activeTab === "claude" ? "var(--color-surface)" : "var(--color-bg)",
              color: activeTab === "claude" ? "var(--color-text)" : "var(--color-text-secondary)",
              cursor: "pointer",
              position: "relative",
              zIndex: activeTab === "claude" ? 1 : 0,
              marginBottom: -1,
            }}
          >
            Claude Desktop
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("vscode")}
            style={{
              padding: "10px 20px",
              fontSize: 13,
              fontWeight: 600,
              border: "1px solid var(--color-border)",
              borderBottom: activeTab === "vscode" ? "1px solid var(--color-surface)" : "1px solid var(--color-border)",
              borderRadius: "8px 8px 0 0",
              background: activeTab === "vscode" ? "var(--color-surface)" : "var(--color-bg)",
              color: activeTab === "vscode" ? "var(--color-text)" : "var(--color-text-secondary)",
              cursor: "pointer",
              position: "relative",
              zIndex: activeTab === "vscode" ? 1 : 0,
              marginBottom: -1,
            }}
          >
            VS Code / Cursor
          </button>
        </div>

        <div style={{
          border: "1px solid var(--color-border)",
          borderRadius: "0 12px 12px 12px",
          padding: 24,
          background: "var(--color-surface)",
        }}>
          {activeTab === "claude" && (
            <div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
                Add this to your Claude Desktop configuration file:
              </div>
              <CodeBlock code={CLAUDE_DESKTOP_CONFIG} />
            </div>
          )}
          {activeTab === "vscode" && (
            <div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
                Add this to your VS Code or Cursor settings:
              </div>
              <CodeBlock code={VSCODE_CONFIG} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default McpPage;
