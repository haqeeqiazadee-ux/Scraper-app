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
// Init
// ---------------------------------------------------------------------------

loadCurrentTab();
loadSettings();
