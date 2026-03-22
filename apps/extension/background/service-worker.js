/**
 * AI Scraper — Background Service Worker
 *
 * Handles messages from the popup, coordinates content script extraction,
 * forwards tasks to the cloud control plane, and manages cloud sync.
 */

import { sendToControlPlane } from "../lib/api.js";
import {
  startCloudSync,
  handleCloudSyncMessage,
  enqueue,
  watchTask,
  getSyncStatus,
} from "../lib/cloud-sync.js";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

/** @type {Map<number, object>} tabId -> last extraction result */
const extractionCache = new Map();

// ---------------------------------------------------------------------------
// Settings helpers
// ---------------------------------------------------------------------------

async function getSettings() {
  const defaults = {
    apiEndpoint: "http://localhost:8000",
    apiKey: "",
    defaultMode: "auto",
    useCloud: false,
  };
  const stored = await chrome.storage.local.get(Object.keys(defaults));
  return { ...defaults, ...stored };
}

// ---------------------------------------------------------------------------
// Content script communication
// ---------------------------------------------------------------------------

/**
 * Ask the content script running in `tabId` to extract page data.
 *
 * @param {number} tabId
 * @param {string} mode  Extraction mode (auto | product | listing | article)
 * @returns {Promise<object>}
 */
async function extractFromTab(tabId, mode) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { action: "extract", mode }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response);
    });
  });
}

/**
 * Send a message to the content script in the given tab.
 *
 * @param {number} tabId
 * @param {object} message
 * @returns {Promise<object>}
 */
async function sendToContentScript(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response);
    });
  });
}

// ---------------------------------------------------------------------------
// Scrape orchestration
// ---------------------------------------------------------------------------

async function handleScrape({ tabId, url, mode }) {
  const settings = await getSettings();
  const effectiveMode = mode || settings.defaultMode;

  // Step 1 — Client-side extraction via content script
  let localData;
  try {
    localData = await extractFromTab(tabId, effectiveMode);
  } catch (err) {
    return { success: false, error: `Content script error: ${err.message}` };
  }

  if (!localData || !localData.success) {
    return {
      success: false,
      error: (localData && localData.error) || "Extraction returned no data",
    };
  }

  // Step 2 — Optionally send to cloud for AI normalization
  if (settings.useCloud && settings.apiKey) {
    try {
      const cloudResult = await sendToControlPlane({
        endpoint: settings.apiEndpoint,
        apiKey: settings.apiKey,
        payload: {
          url,
          mode: effectiveMode,
          raw: localData.data,
        },
      });
      extractionCache.set(tabId, cloudResult);
      return { success: true, data: cloudResult, source: "cloud" };
    } catch (err) {
      // Cloud failed — queue for retry if cloud sync is available
      const syncStatus = getSyncStatus();
      if (syncStatus.connected === false) {
        enqueue("sendExtraction", {
          url,
          mode: effectiveMode,
          data: localData.data,
        });
      }
      console.warn("Cloud extraction failed, using local data:", err.message);
    }
  }

  // Return local extraction
  extractionCache.set(tabId, localData.data);
  return { success: true, data: localData.data, source: "local" };
}

// ---------------------------------------------------------------------------
// Selector picker relay
// ---------------------------------------------------------------------------

async function handleStartSelectorPicker({ tabId }) {
  try {
    const response = await sendToContentScript(tabId, {
      action: "activateSelectorPicker",
    });
    return response;
  } catch (err) {
    return { error: err.message };
  }
}

async function handleStopSelectorPicker({ tabId }) {
  try {
    const response = await sendToContentScript(tabId, {
      action: "deactivateSelectorPicker",
    });
    return response;
  } catch (err) {
    return { error: err.message };
  }
}

// ---------------------------------------------------------------------------
// Message router
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Cloud sync messages
  const cloudSyncActions = [
    "cloudStatus",
    "watchTask",
    "unwatchTask",
    "getQueue",
    "clearQueue",
    "forceHealthCheck",
    "flushQueue",
    "sendToCloud",
  ];

  if (cloudSyncActions.includes(message.action)) {
    return handleCloudSyncMessage(message, sender, sendResponse);
  }

  // Scrape action
  if (message.action === "scrape") {
    handleScrape(message)
      .then(sendResponse)
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  // Cache retrieval
  if (message.action === "getCache") {
    const cached = extractionCache.get(message.tabId) || null;
    sendResponse({ data: cached });
    return false;
  }

  // Selector picker relay
  if (message.action === "startSelectorPicker") {
    handleStartSelectorPicker(message)
      .then(sendResponse)
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.action === "stopSelectorPicker") {
    handleStopSelectorPicker(message)
      .then(sendResponse)
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  // Selector picked — relay from content script to popup
  if (message.action === "selectorPicked") {
    // Forward to popup (it may or may not be open)
    chrome.runtime.sendMessage(message).catch(() => {});
    sendResponse({ relayed: true });
    return false;
  }

  // Selector picker stopped notification
  if (message.action === "selectorPickerStopped") {
    chrome.runtime.sendMessage(message).catch(() => {});
    sendResponse({ relayed: true });
    return false;
  }

  return false;
});

// ---------------------------------------------------------------------------
// Extension lifecycle
// ---------------------------------------------------------------------------

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("AI Scraper installed — opening options for initial setup");
    chrome.runtime.openOptionsPage();
  }
});

// Start cloud sync service
startCloudSync().catch((err) => {
  console.warn("Failed to start cloud sync:", err.message);
});
