/**
 * ConnectionStatus — status indicator component for the popup header.
 *
 * Shows connection state as a colored dot + label:
 *   - Green  dot  + "Cloud"     = cloud control plane connected
 *   - Blue   dot  + "Local"     = local companion connected
 *   - Gray   dot  + "Offline"   = no connection
 *
 * This is a vanilla-JS component (no framework) matching the existing
 * popup architecture (popup.js uses plain DOM manipulation).
 *
 * Usage from popup.js:
 *   import { createConnectionStatus } from "../src/components/ConnectionStatus.js";
 *   const statusEl = createConnectionStatus();
 *   document.querySelector(".header").appendChild(statusEl);
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConnectionState = "local" | "cloud" | "offline";

interface StatusConfig {
  color: string;
  label: string;
  title: string;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const STATE_CONFIG: Record<ConnectionState, StatusConfig> = {
  cloud: {
    color: "#22c55e",   // green
    label: "Cloud",
    title: "Connected to cloud control plane",
  },
  local: {
    color: "#3b82f6",   // blue
    label: "Local",
    title: "Connected to local companion",
  },
  offline: {
    color: "#9ca3af",   // gray
    label: "Offline",
    title: "No connection — requests will be queued",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Create the connection status DOM element.
 * Returns an HTMLElement that can be appended to the popup header.
 */
export function createConnectionStatus(): HTMLElement {
  const container = document.createElement("div");
  container.id = "connection-status";
  container.style.cssText =
    "display:inline-flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;padding:2px 8px;border-radius:12px;background:rgba(255,255,255,0.08);";

  const dot = document.createElement("span");
  dot.id = "connection-dot";
  dot.style.cssText =
    "width:8px;height:8px;border-radius:50%;display:inline-block;transition:background 0.3s;";

  const label = document.createElement("span");
  label.id = "connection-label";
  label.style.cssText = "color:#e5e7eb;font-weight:500;";

  container.appendChild(dot);
  container.appendChild(label);

  // Set initial state
  updateConnectionStatus("offline");

  // Click to refresh status
  container.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "checkHealth" }, (response) => {
      if (response && response.state) {
        updateConnectionStatus(response.state as ConnectionState);
      }
    });
  });

  // Listen for state change broadcasts from the background script
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === "connectionStateChanged" && message.state) {
      updateConnectionStatus(message.state as ConnectionState);
    }
  });

  // Query initial state from background
  chrome.runtime.sendMessage({ action: "getConnectionState" }, (response) => {
    if (response && response.state) {
      updateConnectionStatus(response.state as ConnectionState);
    }
  });

  return container;
}

/**
 * Update the connection status indicator to the given state.
 */
export function updateConnectionStatus(state: ConnectionState): void {
  const config = STATE_CONFIG[state] ?? STATE_CONFIG.offline;

  const dot = document.getElementById("connection-dot");
  const label = document.getElementById("connection-label");
  const container = document.getElementById("connection-status");

  if (dot) {
    dot.style.background = config.color;
  }
  if (label) {
    label.textContent = config.label;
  }
  if (container) {
    container.title = config.title;
  }
}
