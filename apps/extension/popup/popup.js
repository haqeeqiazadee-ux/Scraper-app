/**
 * AI Scraper — Popup Logic
 *
 * Coordinates UI with the background service worker to trigger scrapes,
 * manage selector picker, display results, and handle cloud operations.
 */

const DOM = {
  url: document.getElementById("current-url"),
  mode: document.getElementById("mode-select"),
  scrapeBtn: document.getElementById("scrape-btn"),
  pickerBtn: document.getElementById("picker-btn"),
  settingsBtn: document.getElementById("settings-btn"),
  status: document.getElementById("status"),
  results: document.getElementById("results"),
  resultsSection: document.querySelector(".results-section"),
  cloudIndicator: document.getElementById("cloud-indicator"),
  cloudLabel: document.getElementById("cloud-label"),
  queueBadge: document.getElementById("queue-badge"),
  detectedTypesSection: document.querySelector(".detected-types-section"),
  detectedTypes: document.getElementById("detected-types"),
  cloudActionsSection: document.querySelector(".cloud-actions-section"),
  cloudBtn: document.getElementById("cloud-btn"),
};

/** @type {object|null} Last extraction data for cloud submission */
let lastExtractionData = null;

/** @type {boolean} Whether the selector picker is active */
let selectorPickerActive = false;

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
// Cloud status
// ---------------------------------------------------------------------------

async function updateCloudStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ action: "cloudStatus" });
    if (response && response.connected) {
      DOM.cloudIndicator.className = "cloud-indicator cloud-indicator--online";
      DOM.cloudLabel.textContent = `Cloud: Connected (${response.latency}ms)`;
      if (DOM.cloudBtn) DOM.cloudBtn.disabled = false;
    } else {
      DOM.cloudIndicator.className = "cloud-indicator cloud-indicator--offline";
      DOM.cloudLabel.textContent = "Cloud: Offline";
      if (DOM.cloudBtn) DOM.cloudBtn.disabled = true;
    }

    // Show queue badge if items are queued
    if (response && response.queueSize > 0) {
      DOM.queueBadge.textContent = String(response.queueSize);
      DOM.queueBadge.style.display = "inline";
    } else {
      DOM.queueBadge.style.display = "none";
    }
  } catch {
    DOM.cloudIndicator.className = "cloud-indicator cloud-indicator--offline";
    DOM.cloudLabel.textContent = "Cloud: Unknown";
  }
}

// ---------------------------------------------------------------------------
// Detected types display
// ---------------------------------------------------------------------------

function showDetectedTypes(data) {
  const types = [];

  if (data.jsonLd && Array.isArray(data.jsonLd) && data.jsonLd.length > 0) {
    types.push(`JSON-LD (${data.jsonLd.length})`);
  }
  if (data.meta && typeof data.meta === "object" && Object.keys(data.meta).length > 0) {
    types.push(`Meta (${Object.keys(data.meta).length})`);
  }
  if (data.detectedMode) {
    types.push(`Type: ${data.detectedMode}`);
  }
  if (data.price) {
    types.push("Product");
  }
  if (data.items && Array.isArray(data.items)) {
    types.push(`Items (${data.items.length})`);
  }
  if (data.paragraphs && Array.isArray(data.paragraphs)) {
    types.push(`Paragraphs (${data.paragraphs.length})`);
  }

  if (types.length > 0) {
    DOM.detectedTypes.innerHTML = "";
    for (const t of types) {
      const tag = document.createElement("span");
      tag.className = "detected-type-tag";
      tag.textContent = t;
      DOM.detectedTypes.appendChild(tag);
    }
    DOM.detectedTypesSection.style.display = "block";
  } else {
    DOM.detectedTypesSection.style.display = "none";
  }
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
  DOM.detectedTypesSection.style.display = "none";
  DOM.cloudActionsSection.style.display = "none";

  try {
    const response = await chrome.runtime.sendMessage({
      action: "scrape",
      tabId: tab.id,
      url: tab.url,
      mode,
    });

    if (response && response.success) {
      const sourceLabel = response.source === "cloud" ? " (Cloud)" : " (Local)";
      setStatus(`Extraction complete${sourceLabel}`, "success");
      showResults(response.data);
      showDetectedTypes(response.data);
      lastExtractionData = response.data;

      // Show cloud button if local extraction and cloud is available
      if (response.source === "local") {
        DOM.cloudActionsSection.style.display = "block";
      }
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
// Send to Cloud
// ---------------------------------------------------------------------------

async function handleSendToCloud() {
  if (!lastExtractionData) return;

  const tab = await loadCurrentTab();
  DOM.cloudBtn.disabled = true;
  DOM.cloudBtn.textContent = "Sending...";

  try {
    const response = await chrome.runtime.sendMessage({
      action: "sendToCloud",
      tabId: tab?.id,
      url: tab?.url || "",
      data: lastExtractionData,
    });

    if (response && response.success) {
      setStatus("Cloud processing complete", "success");
      if (response.data) {
        showResults(response.data);
      }
    } else if (response && response.queued) {
      setStatus("Request queued (cloud offline)", "loading");
    } else {
      setStatus(`Cloud error: ${response?.error || "Unknown"}`, "error");
    }
  } catch (err) {
    setStatus(`Cloud error: ${err.message}`, "error");
  } finally {
    DOM.cloudBtn.disabled = false;
    DOM.cloudBtn.textContent = "Send to Cloud";
    updateCloudStatus();
  }
}

// ---------------------------------------------------------------------------
// Selector picker
// ---------------------------------------------------------------------------

async function handleTogglePicker() {
  const tab = await loadCurrentTab();
  if (!tab?.id) return;

  selectorPickerActive = !selectorPickerActive;

  if (selectorPickerActive) {
    DOM.pickerBtn.classList.add("active");
    DOM.pickerBtn.textContent = "ON";
    await chrome.runtime.sendMessage({
      action: "startSelectorPicker",
      tabId: tab.id,
    });
  } else {
    DOM.pickerBtn.classList.remove("active");
    DOM.pickerBtn.textContent = "Pick";
    await chrome.runtime.sendMessage({
      action: "stopSelectorPicker",
      tabId: tab.id,
    });
  }
}

// ---------------------------------------------------------------------------
// Listen for messages from background
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.action === "selectorPicked") {
    const text = `Selector: ${message.selector}\nTag: ${message.tag}\nMatches: ${message.elementCount}\nPreview: ${message.preview}`;
    DOM.results.textContent = text;
    DOM.resultsSection.classList.add("visible");
    setStatus(`Selector picked: ${message.selector}`, "success");
    sendResponse({ received: true });
  }

  if (message.action === "selectorPickerStopped") {
    selectorPickerActive = false;
    DOM.pickerBtn.classList.remove("active");
    DOM.pickerBtn.textContent = "Pick";
    sendResponse({ received: true });
  }

  if (message.action === "taskStatusChanged") {
    setStatus(`Task ${message.taskId.substring(0, 8)}... ${message.status}`, "success");
    sendResponse({ received: true });
  }

  return false;
});

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

DOM.scrapeBtn.addEventListener("click", handleScrape);

DOM.pickerBtn.addEventListener("click", handleTogglePicker);

DOM.settingsBtn.addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

DOM.mode.addEventListener("change", persistMode);

if (DOM.cloudBtn) {
  DOM.cloudBtn.addEventListener("click", handleSendToCloud);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

loadCurrentTab();
loadSettings();
updateCloudStatus();

// Refresh cloud status periodically while popup is open
setInterval(updateCloudStatus, 15000);
