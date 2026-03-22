/**
 * AI Scraper — Background Service Worker
 *
 * Handles messages from the popup, coordinates content script extraction,
 * and optionally forwards tasks to the cloud control plane.
 */

import { sendToControlPlane } from "../lib/api.js";

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
      // Fall back to local data on cloud failure
      console.warn("Cloud extraction failed, using local data:", err.message);
    }
  }

  // Return local extraction
  extractionCache.set(tabId, localData.data);
  return { success: true, data: localData.data, source: "local" };
}

// ---------------------------------------------------------------------------
// Message router
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.action === "scrape") {
    handleScrape(message)
      .then(sendResponse)
      .catch((err) => sendResponse({ success: false, error: err.message }));
    // Return true to indicate async response
    return true;
  }

  if (message.action === "getCache") {
    const cached = extractionCache.get(message.tabId) || null;
    sendResponse({ data: cached });
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
