/**
 * AI Scraper — Popup Logic
 *
 * Coordinates UI with the background service worker to trigger scrapes
 * and display results.
 */

const DOM = {
  url: document.getElementById("current-url"),
  mode: document.getElementById("mode-select"),
  scrapeBtn: document.getElementById("scrape-btn"),
  settingsBtn: document.getElementById("settings-btn"),
  status: document.getElementById("status"),
  results: document.getElementById("results"),
  resultsSection: document.querySelector(".results-section"),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setStatus(text, level = "idle") {
  DOM.status.textContent = text;
  DOM.status.className = `status status--${level}`;
}

function showResults(data) {
  DOM.results.textContent = JSON.stringify(data, null, 2);
  DOM.resultsSection.classList.add("visible");
}

function hideResults() {
  DOM.resultsSection.classList.remove("visible");
  DOM.results.textContent = "";
}

// ---------------------------------------------------------------------------
// Tab info
// ---------------------------------------------------------------------------

async function loadCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    DOM.url.textContent = tab.url;
    DOM.url.title = tab.url;
  }
  return tab;
}

// ---------------------------------------------------------------------------
// Settings persistence
// ---------------------------------------------------------------------------

async function loadSettings() {
  const stored = await chrome.storage.local.get(["extractionMode"]);
  if (stored.extractionMode) {
    DOM.mode.value = stored.extractionMode;
  }
}

function persistMode() {
  chrome.storage.local.set({ extractionMode: DOM.mode.value });
}

// ---------------------------------------------------------------------------
// Scrape action
// ---------------------------------------------------------------------------

async function handleScrape() {
  const tab = await loadCurrentTab();
  if (!tab) {
    setStatus("No active tab found", "error");
    return;
  }

  const mode = DOM.mode.value;
  persistMode();

  DOM.scrapeBtn.disabled = true;
  setStatus("Scraping...", "loading");
  hideResults();

  try {
    const response = await chrome.runtime.sendMessage({
      action: "scrape",
      tabId: tab.id,
      url: tab.url,
      mode,
    });

    if (response && response.success) {
      setStatus("Extraction complete", "success");
      showResults(response.data);
    } else {
      const errMsg = (response && response.error) || "Unknown error";
      setStatus(`Error: ${errMsg}`, "error");
    }
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  } finally {
    DOM.scrapeBtn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

DOM.scrapeBtn.addEventListener("click", handleScrape);

DOM.settingsBtn.addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

DOM.mode.addEventListener("change", persistMode);

// ---------------------------------------------------------------------------
// Connection status indicator
// ---------------------------------------------------------------------------

function initConnectionStatus() {
  const mount = document.getElementById("connection-status-mount");
  if (!mount) return;

  // Create the status indicator inline (matches ConnectionStatus.ts logic
  // but works without TypeScript compilation in the popup context)
  const container = document.createElement("div");
  container.id = "connection-status";
  container.style.cssText =
    "display:inline-flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;padding:2px 8px;border-radius:12px;background:rgba(255,255,255,0.08);";

  const dot = document.createElement("span");
  dot.id = "connection-dot";
  dot.style.cssText =
    "width:8px;height:8px;border-radius:50%;display:inline-block;transition:background 0.3s;background:#9ca3af;";

  const label = document.createElement("span");
  label.id = "connection-label";
  label.style.cssText = "color:#e5e7eb;font-weight:500;";
  label.textContent = "Offline";

  container.appendChild(dot);
  container.appendChild(label);
  mount.appendChild(container);

  const stateConfig = {
    cloud:   { color: "#22c55e", label: "Cloud",   title: "Connected to cloud control plane" },
    local:   { color: "#3b82f6", label: "Local",   title: "Connected to local companion" },
    offline: { color: "#9ca3af", label: "Offline", title: "No connection — requests will be queued" },
  };

  function update(state) {
    const cfg = stateConfig[state] || stateConfig.offline;
    dot.style.background = cfg.color;
    label.textContent = cfg.label;
    container.title = cfg.title;
  }

  // Click to refresh
  container.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "checkHealth" }, (response) => {
      if (response && response.state) update(response.state);
    });
  });

  // Listen for broadcasts
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === "connectionStateChanged" && message.state) {
      update(message.state);
    }
  });

  // Query initial state
  chrome.runtime.sendMessage({ action: "getConnectionState" }, (response) => {
    if (response && response.state) update(response.state);
  });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

loadCurrentTab();
loadSettings();
initConnectionStatus();
