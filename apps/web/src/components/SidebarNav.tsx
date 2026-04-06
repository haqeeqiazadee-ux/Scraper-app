/**
 * SidebarNav — Grouped navigation sidebar with section labels.
 * Groups: CORE, TOOLS, MONITORING, ACCOUNT.
 * Active item has left border accent + background highlight.
 */

import { NavLink, useLocation } from "react-router-dom";
import { GlobalSearch } from "./GlobalSearch";

/* ── SVG Icon components ── */

function IconList() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
      <line x1="2" y1="4" x2="14" y2="4" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="12" x2="14" y2="12" />
    </svg>
  );
}

function IconDatabase() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="8" cy="4" rx="6" ry="2" />
      <path d="M2 4v3c0 1.1 2.7 2 6 2s6-.9 6-2V4" />
      <path d="M2 7v3c0 1.1 2.7 2 6 2s6-.9 6-2V7" />
    </svg>
  );
}

function IconClock() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5" />
      <polyline points="8,4.5 8,8 10.5,10" />
    </svg>
  );
}


function IconTemplate() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="1" width="14" height="4" rx="1" />
      <rect x="1" y="7" width="6" height="8" rx="1" />
      <rect x="9" y="7" width="6" height="8" rx="1" />
    </svg>
  );
}

function IconAmazon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 2L3 5v8a1.5 1.5 0 001.5 1.5h7A1.5 1.5 0 0013 13V5l-2-3z" />
      <line x1="3" y1="5" x2="13" y2="5" />
      <path d="M10.5 7.5a2.5 2.5 0 01-5 0" />
    </svg>
  );
}

function IconMap() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 7c0 4.5-5 7.5-5 7.5S3 11.5 3 7a5 5 0 0110 0z" />
      <circle cx="8" cy="7" r="1.5" />
    </svg>
  );
}

function IconFacebook() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1.5H10.5a3 3 0 00-3 3V7H5.5v2.5H7.5V14.5h2.5V9.5H12l.5-2.5H10V4.5a.5.5 0 01.5-.5H12V1.5z" />
    </svg>
  );
}


function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="4.5" />
      <line x1="10.5" y1="10.5" x2="14" y2="14" />
    </svg>
  );
}


function IconDiff() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="1" width="6" height="14" rx="1" />
      <rect x="9" y="1" width="6" height="14" rx="1" />
      <line x1="3" y1="5" x2="5" y2="5" />
      <line x1="4" y1="4" x2="4" y2="6" />
      <line x1="11" y1="11" x2="13" y2="11" />
    </svg>
  );
}

function IconPlug() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 1.5v3M10 1.5v3M4 4.5h8v3a4 4 0 01-8 0v-3z" />
      <line x1="8" y1="11.5" x2="8" y2="14.5" />
    </svg>
  );
}

function IconKey() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.5 1.5l-1.5 1.5m-4.5 4.5a3.5 3.5 0 11-5 5 3.5 3.5 0 015-5zm0 0L10 7m0 0l2 2 2.5-2.5-2-2" />
    </svg>
  );
}

/* ── Nav groups ── */

interface NavItem {
  to: string;
  label: string;
  Icon: React.FC;
}

interface NavGroupStyled {
  section: string;
  color: string;        // Section label accent color
  items: NavItem[];
}

const NAV_GROUPS: NavGroupStyled[] = [
  {
    section: "SCRAPE",
    color: "#a5b4fc",    // Bright indigo
    items: [
      { to: "/scraper",   label: "Scraper",       Icon: IconSearch },
    ],
  },
  {
    section: "DATA SOURCES",
    color: "#6ee7b7",    // Bright emerald
    items: [
      { to: "/amazon",           label: "Amazon",          Icon: IconAmazon },
      { to: "/google-maps",      label: "Google Maps",     Icon: IconMap },
      { to: "/facebook-groups",  label: "Facebook Groups",  Icon: IconFacebook },
      { to: "/templates",        label: "Templates",       Icon: IconTemplate },
    ],
  },
  {
    section: "ANALYZE",
    color: "#fbbf24",    // Bright amber
    items: [
      { to: "/results",   label: "Results & Export",   Icon: IconDatabase },
      { to: "/changes",   label: "Change Detection",   Icon: IconDiff },
    ],
  },
  {
    section: "AUTOMATE",
    color: "#f9a8d4",    // Bright pink
    items: [
      { to: "/schedules", label: "Schedules",    Icon: IconClock },
      { to: "/mcp",       label: "MCP Server",   Icon: IconPlug },
    ],
  },
  {
    section: "MANAGE",
    color: "#cbd5e1",    // Bright slate
    items: [
      { to: "/tasks",     label: "Tasks",         Icon: IconList },
      { to: "/api-keys",  label: "API Keys",      Icon: IconKey },
    ],
  },
];

/* ── Component ── */

export function SidebarNav() {
  useLocation();

  return (
    <nav
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflowY: "auto",
        paddingBottom: 12,
      }}
    >
      {/* Search box */}
      <GlobalSearch />

      {/* Nav groups */}
      {NAV_GROUPS.map((group, gi) => (
        <div
          key={group.section}
          style={{ marginTop: gi === 0 ? 4 : 16, paddingInline: 8 }}
        >
          {/* Section label with colored accent dot */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 8px 6px",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: group.color,
                flexShrink: 0,
                boxShadow: `0 0 6px ${group.color}80`,
              }}
            />
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 800,
                color: group.color,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
              }}
            >
              {group.section}
            </span>
          </div>

          {/* Items */}
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {group.items.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "7px 10px 7px 14px",
                  borderRadius: 8,
                  color: isActive ? "#ffffff" : "rgba(255,255,255,0.6)",
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 400,
                  textDecoration: "none",
                  background: isActive
                    ? `linear-gradient(135deg, ${group.color}33, ${group.color}18)`
                    : "transparent",
                  borderLeft: isActive
                    ? `2.5px solid ${group.color}`
                    : "2.5px solid transparent",
                  transition: "all 0.2s ease",
                })}
                className={({ isActive }) => (isActive ? "active" : "")}
                onMouseEnter={(e) => {
                  const el = e.currentTarget;
                  if (!el.classList.contains("active")) {
                    el.style.background = "rgba(255,255,255,0.05)";
                    el.style.color = "#ffffff";
                    el.style.borderLeftColor = `${group.color}66`;
                  }
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget;
                  if (!el.classList.contains("active")) {
                    el.style.background = "transparent";
                    el.style.color = "rgba(255,255,255,0.6)";
                    el.style.borderLeftColor = "transparent";
                  }
                }}
              >
                <span
                  style={{
                    width: 18,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    opacity: 0.8,
                  }}
                >
                  <Icon />
                </span>
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
