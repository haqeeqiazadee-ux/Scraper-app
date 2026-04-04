/**
 * SidebarNav — Grouped navigation sidebar with section labels.
 * Groups: CORE, TOOLS, MONITORING, ACCOUNT.
 * Active item has left border accent + background highlight.
 */

import { NavLink, useLocation } from "react-router-dom";
import { GlobalSearch } from "./GlobalSearch";

/* ── SVG Icon components ── */

function IconGrid() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="1" width="6" height="6" rx="1" />
      <rect x="9" y="1" width="6" height="6" rx="1" />
      <rect x="1" y="9" width="6" height="6" rx="1" />
      <rect x="9" y="9" width="6" height="6" rx="1" />
    </svg>
  );
}

function IconList() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
      <line x1="2" y1="4" x2="14" y2="4" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="12" x2="14" y2="12" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1.5L2 4v4c0 3.3 2.5 5.7 6 6.5 3.5-.8 6-3.2 6-6.5V4L8 1.5z" />
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

function IconCompass() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5" />
      <polygon points="10.5,5.5 6.5,8 5.5,10.5 9.5,8" fill="currentColor" stroke="none" />
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

function IconActivity() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1,8 4,4 6,11 9,5 11,9 15,8" />
    </svg>
  );
}

function IconGlobe() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5" />
      <line x1="1.5" y1="8" x2="14.5" y2="8" />
      <path d="M8 1.5a9.5 9.5 0 0 1 0 13" />
      <path d="M8 1.5a9.5 9.5 0 0 0 0 13" />
    </svg>
  );
}

function IconWebhook() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="4.5" cy="12.5" r="2" />
      <circle cx="11.5" cy="12.5" r="2" />
      <circle cx="8" cy="3.5" r="2" />
      <path d="M8 5.5L4.5 10.5" />
      <path d="M8 5.5L11.5 10.5" />
    </svg>
  );
}

function IconCreditCard() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="3.5" width="14" height="9" rx="1.5" />
      <line x1="1" y1="7" x2="15" y2="7" />
      <line x1="4" y1="10.5" x2="7" y2="10.5" />
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

function IconSpider() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="6" r="2.5" />
      <path d="M5.5 6L2 3M10.5 6L14 3M5.5 7L1.5 8.5M10.5 7L14.5 8.5M6 8.5L3 12M10 8.5L13 12" />
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

function IconCode() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="5 4 1.5 8 5 12" />
      <polyline points="11 4 14.5 8 11 12" />
      <line x1="9.5" y1="2.5" x2="6.5" y2="13.5" />
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

/* ── Nav groups ── */

interface NavItem {
  to: string;
  label: string;
  Icon: React.FC;
}

interface NavGroup {
  section: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    section: "CORE",
    items: [
      { to: "/dashboard", label: "Dashboard", Icon: IconGrid },
      { to: "/tasks",     label: "Tasks",     Icon: IconList },
      { to: "/policies",  label: "Policies",  Icon: IconShield },
      { to: "/results",   label: "Results",   Icon: IconDatabase },
    ],
  },
  {
    section: "TOOLS",
    items: [
      { to: "/templates",     label: "Templates",     Icon: IconTemplate },
      { to: "/route-tester",  label: "Route Tester",  Icon: IconCompass },
      { to: "/scrape-test",   label: "Scrape Tester", Icon: IconDatabase },
      { to: "/amazon",        label: "Amazon / Keepa", Icon: IconAmazon },
      { to: "/google-maps",   label: "Google Maps",   Icon: IconMap },
      { to: "/crawl",         label: "Crawl",         Icon: IconSpider },
      { to: "/search",        label: "Search",        Icon: IconSearch },
      { to: "/extract",       label: "Extract",       Icon: IconCode },
      { to: "/changes",       label: "Changes",       Icon: IconDiff },
      { to: "/schedules",     label: "Schedules",     Icon: IconClock },
    ],
  },
  {
    section: "MONITORING",
    items: [
      { to: "/sessions", label: "Sessions", Icon: IconActivity },
      { to: "/proxies",  label: "Proxies",  Icon: IconGlobe },
      { to: "/webhooks", label: "Webhooks", Icon: IconWebhook },
    ],
  },
  {
    section: "INTEGRATION",
    items: [
      { to: "/mcp", label: "MCP Server", Icon: IconPlug },
    ],
  },
  {
    section: "ACCOUNT",
    items: [
      { to: "/billing", label: "Billing", Icon: IconCreditCard },
    ],
  },
];

/* ── Component ── */

export function SidebarNav() {
  // useLocation consumed only for re-render on route change; NavLink handles
  // the active class itself.
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
          style={{ marginTop: gi === 0 ? 4 : 12, paddingInline: 8 }}
        >
          {/* Section label */}
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "rgba(255,255,255,0.3)",
              letterSpacing: "0.08em",
              padding: "4px 8px 6px",
              textTransform: "uppercase",
            }}
          >
            {group.section}
          </div>

          {/* Items */}
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {group.items.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 10px 8px 10px",
                  borderRadius: "var(--radius-md)",
                  color: isActive ? "#ffffff" : "rgba(255,255,255,0.65)",
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 500,
                  textDecoration: "none",
                  background: isActive
                    ? "rgba(37,99,235,0.5)"
                    : "transparent",
                  borderLeft: isActive
                    ? "2px solid var(--color-primary)"
                    : "2px solid transparent",
                  transition:
                    "background 0.15s, color 0.15s, border-color 0.15s",
                  marginLeft: isActive ? 0 : 0,
                })}
                className={({ isActive }) => (isActive ? "active" : "")}
                onMouseEnter={(e) => {
                  const el = e.currentTarget;
                  if (!el.classList.contains("active")) {
                    el.style.background = "rgba(255,255,255,0.06)";
                    el.style.color = "#ffffff";
                  }
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget;
                  if (!el.classList.contains("active")) {
                    el.style.background = "transparent";
                    el.style.color = "rgba(255,255,255,0.65)";
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
                    opacity: 0.85,
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
