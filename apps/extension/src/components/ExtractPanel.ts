/**
 * AI Scraper — Extract Panel Module
 *
 * UI panel for the popup that shows:
 * - Current page URL
 * - Detected data types
 * - Extraction preview with selector results
 * - "Send to Cloud" button
 * - Selector picker toggle
 *
 * This module manipulates the popup DOM directly (no framework).
 * It communicates with the background service worker via chrome.runtime messages.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DetectedDataType {
  type: string;
  label: string;
  count: number;
  confidence: number;
}

interface PreviewItem {
  name: string;
  value: string;
  selector: string;
}

interface ExtractPanelState {
  url: string;
  detectedTypes: DetectedDataType[];
  previews: PreviewItem[];
  isExtracting: boolean;
  isSendingToCloud: boolean;
  cloudConnected: boolean;
  selectorPickerActive: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// DOM references and state
// ---------------------------------------------------------------------------

let panelContainer: HTMLElement | null = null;

const state: ExtractPanelState = {
  url: "",
  detectedTypes: [],
  previews: [],
  isExtracting: false,
  isSendingToCloud: false,
  cloudConnected: false,
  selectorPickerActive: false,
  error: null,
};

// ---------------------------------------------------------------------------
// Panel creation
// ---------------------------------------------------------------------------

/**
 * Initialize the extract panel inside the given container element.
 * Call this from the popup script after DOM is loaded.
 */
export function initExtractPanel(container: HTMLElement): void {
  panelContainer = container;
  render();
  checkCloudStatus();
}

/**
 * Update the current page URL and trigger detection.
 */
export function setPageUrl(url: string): void {
  state.url = url;
  render();
}

/**
 * Update detected data types from content script analysis.
 */
export function setDetectedTypes(types: DetectedDataType[]): void {
  state.detectedTypes = types;
  render();
}

// ---------------------------------------------------------------------------
// Cloud status
// ---------------------------------------------------------------------------

async function checkCloudStatus(): Promise<void> {
  try {
    const response = await chrome.runtime.sendMessage({
      action: "cloudStatus",
    });
    state.cloudConnected = response?.connected || false;
  } catch {
    state.cloudConnected = false;
  }
  render();
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function handleExtract(): Promise<void> {
  if (state.isExtracting) return;

  state.isExtracting = true;
  state.error = null;
  state.previews = [];
  render();

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("No active tab");

    const response = await chrome.runtime.sendMessage({
      action: "scrape",
      tabId: tab.id,
      url: tab.url,
      mode: "auto",
    });

    if (response?.success && response.data) {
      const data = response.data as Record<string, unknown>;
      state.previews = buildPreviews(data);

      // Detect types from data
      state.detectedTypes = detectTypes(data);
    } else {
      state.error = response?.error || "Extraction failed";
    }
  } catch (err: unknown) {
    state.error = (err as Error).message || "Unknown error";
  } finally {
    state.isExtracting = false;
    render();
  }
}

async function handleSendToCloud(): Promise<void> {
  if (state.isSendingToCloud || state.previews.length === 0) return;

  state.isSendingToCloud = true;
  state.error = null;
  render();

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("No active tab");

    const response = await chrome.runtime.sendMessage({
      action: "sendToCloud",
      tabId: tab.id,
      url: tab.url || state.url,
      data: Object.fromEntries(
        state.previews.map((p) => [p.name, p.value])
      ),
    });

    if (response?.success) {
      state.previews = buildPreviews(response.data || {});
    } else {
      state.error = response?.error || "Cloud processing failed";
    }
  } catch (err: unknown) {
    state.error = (err as Error).message || "Cloud error";
  } finally {
    state.isSendingToCloud = false;
    render();
  }
}

async function handleToggleSelectorPicker(): Promise<void> {
  state.selectorPickerActive = !state.selectorPickerActive;
  render();

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;

    await chrome.runtime.sendMessage({
      action: state.selectorPickerActive ? "startSelectorPicker" : "stopSelectorPicker",
      tabId: tab.id,
    });
  } catch {
    state.selectorPickerActive = false;
    render();
  }
}

// ---------------------------------------------------------------------------
// Data processing
// ---------------------------------------------------------------------------

function buildPreviews(data: Record<string, unknown>): PreviewItem[] {
  const previews: PreviewItem[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) continue;
    const strValue = typeof value === "object"
      ? JSON.stringify(value).substring(0, 200)
      : String(value).substring(0, 200);
    previews.push({
      name: key,
      value: strValue,
      selector: "",
    });
  }
  return previews.slice(0, 20);
}

function detectTypes(data: Record<string, unknown>): DetectedDataType[] {
  const types: DetectedDataType[] = [];

  if (data.jsonLd && Array.isArray(data.jsonLd) && data.jsonLd.length > 0) {
    types.push({
      type: "json-ld",
      label: "JSON-LD Structured Data",
      count: data.jsonLd.length,
      confidence: 0.95,
    });
  }

  if (data.meta && typeof data.meta === "object" && Object.keys(data.meta as object).length > 0) {
    types.push({
      type: "meta",
      label: "Meta Tags",
      count: Object.keys(data.meta as object).length,
      confidence: 0.8,
    });
  }

  if (data.price || data.detectedMode === "product") {
    types.push({
      type: "product",
      label: "Product Data",
      count: 1,
      confidence: data.price ? 0.9 : 0.6,
    });
  }

  if (data.items && Array.isArray(data.items)) {
    types.push({
      type: "listing",
      label: "List Items",
      count: data.items.length,
      confidence: 0.7,
    });
  }

  if (data.paragraphs && Array.isArray(data.paragraphs)) {
    types.push({
      type: "article",
      label: "Article Content",
      count: data.paragraphs.length,
      confidence: 0.75,
    });
  }

  return types;
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function render(): void {
  if (!panelContainer) return;

  panelContainer.innerHTML = "";

  // URL display
  const urlSection = el("div", "ep-section");
  urlSection.appendChild(label("Current Page"));
  const urlBox = el("div", "ep-url");
  urlBox.textContent = state.url || "(no page)";
  urlBox.title = state.url;
  urlSection.appendChild(urlBox);
  panelContainer.appendChild(urlSection);

  // Detected data types
  if (state.detectedTypes.length > 0) {
    const typesSection = el("div", "ep-section");
    typesSection.appendChild(label("Detected Data"));
    const typesList = el("div", "ep-types");
    for (const dt of state.detectedTypes) {
      const tag = el("span", "ep-tag");
      tag.textContent = `${dt.label} (${dt.count})`;
      tag.title = `Confidence: ${Math.round(dt.confidence * 100)}%`;
      typesList.appendChild(tag);
    }
    typesSection.appendChild(typesList);
    panelContainer.appendChild(typesSection);
  }

  // Action buttons row
  const actionsSection = el("div", "ep-section ep-actions");

  const extractBtn = el("button", "ep-btn ep-btn--primary") as HTMLButtonElement;
  extractBtn.textContent = state.isExtracting ? "Extracting..." : "Extract Data";
  extractBtn.disabled = state.isExtracting;
  extractBtn.addEventListener("click", handleExtract);
  actionsSection.appendChild(extractBtn);

  const pickerBtn = el(
    "button",
    `ep-btn ep-btn--secondary ${state.selectorPickerActive ? "ep-btn--active" : ""}`
  ) as HTMLButtonElement;
  pickerBtn.textContent = state.selectorPickerActive ? "Picker ON" : "Pick Selector";
  pickerBtn.addEventListener("click", handleToggleSelectorPicker);
  actionsSection.appendChild(pickerBtn);

  panelContainer.appendChild(actionsSection);

  // Preview section
  if (state.previews.length > 0) {
    const previewSection = el("div", "ep-section");
    previewSection.appendChild(label("Extraction Preview"));
    const previewList = el("div", "ep-previews");

    for (const item of state.previews) {
      const row = el("div", "ep-preview-row");
      const nameEl = el("span", "ep-preview-name");
      nameEl.textContent = item.name;
      const valueEl = el("span", "ep-preview-value");
      valueEl.textContent = item.value;
      valueEl.title = item.value;
      row.appendChild(nameEl);
      row.appendChild(valueEl);
      previewList.appendChild(row);
    }

    previewSection.appendChild(previewList);
    panelContainer.appendChild(previewSection);

    // Send to cloud button
    const cloudSection = el("div", "ep-section");
    const cloudBtn = el("button", "ep-btn ep-btn--cloud") as HTMLButtonElement;
    cloudBtn.textContent = state.isSendingToCloud
      ? "Sending..."
      : state.cloudConnected
      ? "Send to Cloud"
      : "Cloud Offline";
    cloudBtn.disabled = state.isSendingToCloud || !state.cloudConnected;
    cloudBtn.addEventListener("click", handleSendToCloud);
    cloudSection.appendChild(cloudBtn);

    if (!state.cloudConnected) {
      const hint = el("div", "ep-hint");
      hint.textContent = "Enable cloud mode in Settings to use AI normalization.";
      cloudSection.appendChild(hint);
    }

    panelContainer.appendChild(cloudSection);
  }

  // Error display
  if (state.error) {
    const errorSection = el("div", "ep-section");
    const errorBox = el("div", "ep-error");
    errorBox.textContent = state.error;
    errorSection.appendChild(errorBox);
    panelContainer.appendChild(errorSection);
  }
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function el(tag: string, className: string): HTMLElement {
  const element = document.createElement(tag.split(" ")[0]);
  element.className = className;
  return element;
}

function label(text: string): HTMLElement {
  const lbl = el("label", "ep-label");
  lbl.textContent = text;
  return lbl;
}

// ---------------------------------------------------------------------------
// Panel styles (injected once)
// ---------------------------------------------------------------------------

let stylesInjected = false;

export function injectPanelStyles(): void {
  if (stylesInjected) return;
  stylesInjected = true;

  const style = document.createElement("style");
  style.textContent = `
    .ep-section { margin-bottom: 10px; }
    .ep-actions { display: flex; gap: 8px; }
    .ep-label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--color-text-muted, #8888aa);
      margin-bottom: 4px;
    }
    .ep-url {
      background: var(--color-surface, #222240);
      border: 1px solid var(--color-border, #333360);
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .ep-types { display: flex; flex-wrap: wrap; gap: 4px; }
    .ep-tag {
      display: inline-block;
      background: rgba(79, 140, 255, 0.15);
      color: var(--color-primary, #4f8cff);
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 600;
    }
    .ep-btn {
      flex: 1;
      padding: 8px 12px;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s;
    }
    .ep-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .ep-btn--primary {
      background: var(--color-primary, #4f8cff);
      color: #fff;
    }
    .ep-btn--primary:hover:not(:disabled) {
      background: var(--color-primary-hover, #3a74e0);
    }
    .ep-btn--secondary {
      background: var(--color-surface, #222240);
      color: var(--color-text, #e0e0f0);
      border: 1px solid var(--color-border, #333360);
    }
    .ep-btn--secondary:hover:not(:disabled) {
      border-color: var(--color-primary, #4f8cff);
    }
    .ep-btn--active {
      border-color: var(--color-primary, #4f8cff);
      background: rgba(79, 140, 255, 0.15);
    }
    .ep-btn--cloud {
      width: 100%;
      padding: 10px;
      background: linear-gradient(135deg, #4f8cff 0%, #6c5ce7 100%);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    .ep-btn--cloud:disabled {
      background: var(--color-border, #333360);
      color: var(--color-text-muted, #8888aa);
      cursor: not-allowed;
    }
    .ep-previews {
      background: var(--color-surface, #222240);
      border: 1px solid var(--color-border, #333360);
      border-radius: 6px;
      max-height: 150px;
      overflow-y: auto;
    }
    .ep-preview-row {
      display: flex;
      padding: 4px 8px;
      border-bottom: 1px solid var(--color-border, #333360);
      font-size: 11px;
    }
    .ep-preview-row:last-child { border-bottom: none; }
    .ep-preview-name {
      flex: 0 0 80px;
      font-weight: 600;
      color: var(--color-primary, #4f8cff);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ep-preview-value {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--color-text, #e0e0f0);
    }
    .ep-error {
      background: rgba(244, 67, 54, 0.1);
      color: var(--color-error, #f44336);
      border: 1px solid rgba(244, 67, 54, 0.3);
      border-radius: 6px;
      padding: 8px;
      font-size: 12px;
    }
    .ep-hint {
      font-size: 11px;
      color: var(--color-text-muted, #8888aa);
      margin-top: 4px;
      text-align: center;
    }
  `;
  document.head.appendChild(style);
}

// ---------------------------------------------------------------------------
// Listen for selector picker results
// ---------------------------------------------------------------------------

if (typeof chrome !== "undefined" && chrome.runtime) {
  chrome.runtime.onMessage.addListener((message: any, _sender: any, sendResponse: any) => {
    if (message.action === "selectorPicked" && message.selector) {
      state.previews.push({
        name: `picked_${state.previews.length}`,
        value: message.preview || "",
        selector: message.selector,
      });
      render();
      sendResponse({ received: true });
    }
    return false;
  });
}
