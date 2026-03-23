/**
 * GlobalSearch — Command-palette style search with Cmd+K shortcut.
 * Searches tasks and policies, shows categorized dropdown with keyboard nav.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTaskList } from "../hooks/useTasks";
import { usePolicyList } from "../hooks/usePolicies";

interface SearchResult {
  id: string;
  label: string;
  sub: string;
  href: string;
  category: "Tasks" | "Policies";
}

const ICON_SEARCH = (
  <svg
    width="14"
    height="14"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="6.5" cy="6.5" r="4.5" />
    <line x1="10.5" y1="10.5" x2="14" y2="14" />
  </svg>
);

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { data: tasksData } = useTaskList({ limit: 100 });
  const { data: policiesData } = usePolicyList({ limit: 100 });

  /* Cmd+K / Ctrl+K global shortcut */
  useEffect(() => {
    function onGlobal(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    document.addEventListener("keydown", onGlobal);
    return () => document.removeEventListener("keydown", onGlobal);
  }, []);

  /* Build filtered results */
  const results: SearchResult[] = [];

  const q = query.trim().toLowerCase();

  if (q) {
    const taskItems = tasksData?.items ?? [];
    for (const t of taskItems) {
      if (t.name.toLowerCase().includes(q) || t.url.toLowerCase().includes(q)) {
        results.push({
          id: t.id,
          label: t.name || "(unnamed)",
          sub: t.url,
          href: `/tasks/${t.id}`,
          category: "Tasks",
        });
      }
    }
    const policyItems = policiesData?.items ?? [];
    for (const p of policyItems) {
      const domains = p.target_domains.join(", ");
      if (p.name.toLowerCase().includes(q) || domains.toLowerCase().includes(q)) {
        results.push({
          id: p.id,
          label: p.name,
          sub: domains || p.preferred_lane,
          href: `/policies/${p.id}`,
          category: "Policies",
        });
      }
    }
  }

  /* Reset active index when results change */
  useEffect(() => {
    setActiveIdx(0);
  }, [results.length, query]);

  const handleSelect = useCallback(
    (href: string) => {
      navigate(href);
      setQuery("");
      setOpen(false);
      inputRef.current?.blur();
    },
    [navigate],
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || results.length === 0) {
      if (e.key === "Escape") {
        setOpen(false);
        inputRef.current?.blur();
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const r = results[activeIdx];
      if (r) handleSelect(r.href);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  /* Scroll active item into view */
  useEffect(() => {
    if (!listRef.current) return;
    const active = listRef.current.querySelector<HTMLDivElement>(
      "[data-active='true']",
    );
    active?.scrollIntoView({ block: "nearest" });
  }, [activeIdx]);

  /* Group results by category */
  const grouped: Record<string, SearchResult[]> = {};
  for (const r of results) {
    if (!grouped[r.category]) grouped[r.category] = [];
    grouped[r.category].push(r);
  }
  const categories = Object.keys(grouped) as ("Tasks" | "Policies")[];

  const showDropdown = open && query.trim().length > 0;

  return (
    <div style={{ position: "relative", padding: "8px 12px" }}>
      {/* Input */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "7px 10px",
          background: "rgba(255,255,255,0.06)",
          border: `1px solid ${open ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.1)"}`,
          borderRadius: "var(--radius-md)",
          transition: "border-color 0.15s, background 0.15s",
          cursor: "text",
        }}
        onClick={() => inputRef.current?.focus()}
      >
        <span style={{ color: "rgba(255,255,255,0.4)", flexShrink: 0 }}>
          {ICON_SEARCH}
        </span>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            /* Delay so clicks on results register first */
            setTimeout(() => setOpen(false), 150);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search…"
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            fontSize: 13,
            color: "rgba(255,255,255,0.85)",
            fontFamily: "inherit",
          }}
          aria-label="Search tasks and policies"
          autoComplete="off"
          spellCheck={false}
        />
        <span
          style={{
            flexShrink: 0,
            fontSize: 10,
            fontWeight: 600,
            color: "rgba(255,255,255,0.3)",
            background: "rgba(255,255,255,0.08)",
            borderRadius: 4,
            padding: "2px 5px",
            letterSpacing: "0.02em",
            pointerEvents: "none",
          }}
        >
          ⌘K
        </span>
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          ref={listRef}
          style={{
            position: "absolute",
            top: "calc(100% - 4px)",
            left: 12,
            right: 12,
            zIndex: 2000,
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            boxShadow:
              "0 8px 24px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)",
            overflow: "hidden",
            maxHeight: 320,
            overflowY: "auto",
          }}
        >
          {results.length === 0 ? (
            <div
              style={{
                padding: "14px 16px",
                fontSize: 13,
                color: "var(--color-text-secondary)",
                textAlign: "center",
              }}
            >
              No results for &ldquo;{query}&rdquo;
            </div>
          ) : (
            categories.map((cat) => {
              let flatIdx =
                cat === "Tasks" ? 0 : (grouped["Tasks"]?.length ?? 0);
              return (
                <div key={cat}>
                  {/* Category label */}
                  <div
                    style={{
                      padding: "6px 12px 4px",
                      fontSize: 10,
                      fontWeight: 700,
                      color: "var(--color-text-secondary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      borderTop:
                        cat !== categories[0]
                          ? "1px solid var(--color-border)"
                          : "none",
                      background: "var(--color-bg)",
                    }}
                  >
                    {cat}
                  </div>
                  {grouped[cat].map((r) => {
                    const idx = flatIdx++;
                    const isActive = idx === activeIdx;
                    return (
                      <div
                        key={r.id}
                        data-active={isActive}
                        onMouseDown={() => handleSelect(r.href)}
                        onMouseEnter={() => setActiveIdx(idx)}
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 2,
                          padding: "8px 12px",
                          cursor: "pointer",
                          background: isActive
                            ? "rgba(37,99,235,0.06)"
                            : "transparent",
                          borderLeft: isActive
                            ? "2px solid var(--color-primary)"
                            : "2px solid transparent",
                          transition: "background 0.1s",
                        }}
                      >
                        <span
                          style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: "var(--color-text)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {r.label}
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            color: "var(--color-text-secondary)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {r.sub}
                        </span>
                      </div>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
