/**
 * AI Scraper — Options Page Logic
 *
 * Persists user settings to chrome.storage.local.
 */

const DOM = {
  apiEndpoint: document.getElementById("api-endpoint"),
  apiKey: document.getElementById("api-key"),
  defaultMode: document.getElementById("default-mode"),
  useCloud: document.getElementById("use-cloud"),
  saveBtn: document.getElementById("save-btn"),
  toast: document.getElementById("toast"),
};

const STORAGE_KEYS = ["apiEndpoint", "apiKey", "defaultMode", "useCloud"];

const DEFAULTS = {
  apiEndpoint: "http://localhost:8000",
  apiKey: "",
  defaultMode: "auto",
  useCloud: false,
};

// ---------------------------------------------------------------------------
// Load / Save
// ---------------------------------------------------------------------------

async function loadSettings() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS);
  const settings = { ...DEFAULTS, ...stored };

  DOM.apiEndpoint.value = settings.apiEndpoint;
  DOM.apiKey.value = settings.apiKey;
  DOM.defaultMode.value = settings.defaultMode;
  DOM.useCloud.checked = settings.useCloud;
}

async function saveSettings() {
  const settings = {
    apiEndpoint: DOM.apiEndpoint.value.trim() || DEFAULTS.apiEndpoint,
    apiKey: DOM.apiKey.value.trim(),
    defaultMode: DOM.defaultMode.value,
    useCloud: DOM.useCloud.checked,
  };

  await chrome.storage.local.set(settings);
  showToast();
}

// ---------------------------------------------------------------------------
// UI feedback
// ---------------------------------------------------------------------------

let toastTimer = null;

function showToast() {
  DOM.toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    DOM.toast.classList.remove("visible");
  }, 2000);
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

DOM.saveBtn.addEventListener("click", saveSettings);

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

loadSettings();
