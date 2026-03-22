/**
 * AI Scraper — Visual Selector Picker
 *
 * Injects into the page as a content script module. When activated,
 * it lets the user hover over elements to highlight them and click
 * to generate an optimal CSS selector. Communicates the selected
 * selector back to the popup via chrome.runtime messages.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PickerState {
  active: boolean;
  hoveredElement: Element | null;
  selectedElements: Element[];
  overlay: HTMLElement | null;
  tooltip: HTMLElement | null;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const PICKER_OVERLAY_ID = "ai-scraper-picker-overlay";
const PICKER_TOOLTIP_ID = "ai-scraper-picker-tooltip";
const PICKER_HIGHLIGHT_CLASS = "ai-scraper-picker-highlight";
const PICKER_SELECTED_CLASS = "ai-scraper-picker-selected";

const pickerState: PickerState = {
  active: false,
  hoveredElement: null,
  selectedElements: [],
  overlay: null,
  tooltip: null,
};

// ---------------------------------------------------------------------------
// Style injection
// ---------------------------------------------------------------------------

let pickerStylesInjected = false;

function injectPickerStyles(): void {
  if (pickerStylesInjected) return;
  pickerStylesInjected = true;

  const style = document.createElement("style");
  style.id = "ai-scraper-picker-styles";
  style.textContent = `
    .${PICKER_HIGHLIGHT_CLASS} {
      outline: 2px solid #4f8cff !important;
      outline-offset: -1px;
      background: rgba(79, 140, 255, 0.12) !important;
      cursor: crosshair !important;
      transition: outline-color 0.1s, background 0.1s;
    }
    .${PICKER_SELECTED_CLASS} {
      outline: 2px solid #4caf50 !important;
      outline-offset: -1px;
      background: rgba(76, 175, 80, 0.12) !important;
    }
    #${PICKER_OVERLAY_ID} {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 2147483646;
      cursor: crosshair;
      pointer-events: none;
    }
    #${PICKER_TOOLTIP_ID} {
      position: fixed;
      z-index: 2147483647;
      background: #1a1a2e;
      color: #e0e0f0;
      border: 1px solid #4f8cff;
      border-radius: 4px;
      padding: 4px 8px;
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 11px;
      max-width: 400px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      pointer-events: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    }
  `;
  document.head.appendChild(style);
}

// ---------------------------------------------------------------------------
// Selector generation
// ---------------------------------------------------------------------------

/**
 * Generate an optimal CSS selector for the given element.
 * Tries ID, then unique class, then nth-child path.
 */
function generateSelector(element: Element): string {
  // If element has an ID, use it (most specific)
  if (element.id) {
    return `#${CSS.escape(element.id)}`;
  }

  // Try unique class-based selector
  const classSelector = getUniqueClassSelector(element);
  if (classSelector) return classSelector;

  // Try attribute-based selector
  const attrSelector = getAttributeSelector(element);
  if (attrSelector) return attrSelector;

  // Fall back to path-based selector
  return getPathSelector(element);
}

function getUniqueClassSelector(element: Element): string | null {
  if (!element.classList || element.classList.length === 0) return null;

  const tag = element.tagName.toLowerCase();

  // Try tag + single class combinations
  for (const cls of element.classList) {
    if (cls.startsWith("ai-scraper-")) continue; // Skip our own classes
    const selector = `${tag}.${CSS.escape(cls)}`;
    try {
      if (document.querySelectorAll(selector).length === 1) {
        return selector;
      }
    } catch {
      continue;
    }
  }

  // Try tag + multiple classes
  if (element.classList.length > 1) {
    const classStr = Array.from(element.classList)
      .filter((c) => !c.startsWith("ai-scraper-"))
      .map((c) => `.${CSS.escape(c)}`)
      .join("");
    if (classStr) {
      const selector = `${tag}${classStr}`;
      try {
        if (document.querySelectorAll(selector).length === 1) {
          return selector;
        }
      } catch {
        // Fall through
      }
    }
  }

  return null;
}

function getAttributeSelector(element: Element): string | null {
  const tag = element.tagName.toLowerCase();
  const importantAttrs = ["data-testid", "data-id", "name", "role", "type", "aria-label"];

  for (const attr of importantAttrs) {
    const value = element.getAttribute(attr);
    if (value) {
      const selector = `${tag}[${attr}="${CSS.escape(value)}"]`;
      try {
        if (document.querySelectorAll(selector).length === 1) {
          return selector;
        }
      } catch {
        continue;
      }
    }
  }

  return null;
}

function getPathSelector(element: Element): string {
  const parts: string[] = [];
  let current: Element | null = element;

  while (current && current !== document.documentElement) {
    let selector = current.tagName.toLowerCase();

    if (current.id) {
      parts.unshift(`#${CSS.escape(current.id)}`);
      break;
    }

    // Add nth-child if there are siblings of the same tag
    const parent = current.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(
        (s) => s.tagName === current!.tagName
      );
      if (siblings.length > 1) {
        const index = siblings.indexOf(current) + 1;
        selector += `:nth-child(${index})`;
      }
    }

    parts.unshift(selector);
    current = parent;

    // Limit depth to keep selectors reasonable
    if (parts.length >= 5) break;
  }

  return parts.join(" > ");
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

function onMouseMove(event: MouseEvent): void {
  if (!pickerState.active) return;

  const target = document.elementFromPoint(event.clientX, event.clientY);
  if (!target || target === pickerState.hoveredElement) return;

  // Remove highlight from previous element
  if (pickerState.hoveredElement) {
    pickerState.hoveredElement.classList.remove(PICKER_HIGHLIGHT_CLASS);
  }

  // Skip our own UI elements
  if (
    target.id === PICKER_OVERLAY_ID ||
    target.id === PICKER_TOOLTIP_ID ||
    target.closest(`#${PICKER_OVERLAY_ID}`)
  ) {
    return;
  }

  pickerState.hoveredElement = target;
  target.classList.add(PICKER_HIGHLIGHT_CLASS);

  // Update tooltip
  updateTooltip(target, event.clientX, event.clientY);
}

function onClick(event: MouseEvent): void {
  if (!pickerState.active) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();

  const target = pickerState.hoveredElement;
  if (!target) return;

  // Generate selector
  const selector = generateSelector(target);
  const preview = target.textContent?.trim().substring(0, 100) || "";

  // Mark as selected
  target.classList.remove(PICKER_HIGHLIGHT_CLASS);
  target.classList.add(PICKER_SELECTED_CLASS);
  pickerState.selectedElements.push(target);

  // Send selector to popup via background
  chrome.runtime.sendMessage({
    action: "selectorPicked",
    selector,
    preview,
    tag: target.tagName.toLowerCase(),
    elementCount: document.querySelectorAll(selector).length,
  });
}

function onKeyDown(event: KeyboardEvent): void {
  if (!pickerState.active) return;

  // Escape to cancel
  if (event.key === "Escape") {
    deactivatePicker();
  }
}

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

function updateTooltip(element: Element, x: number, y: number): void {
  if (!pickerState.tooltip) return;

  const selector = generateSelector(element);
  const tag = element.tagName.toLowerCase();
  const classes = element.className
    ? `.${Array.from(element.classList)
        .filter((c) => !c.startsWith("ai-scraper-"))
        .join(".")}`
    : "";

  pickerState.tooltip.textContent = `${tag}${classes} → ${selector}`;
  pickerState.tooltip.style.display = "block";

  // Position tooltip near cursor, but within viewport
  const tooltipRect = pickerState.tooltip.getBoundingClientRect();
  let left = x + 12;
  let top = y + 12;

  if (left + tooltipRect.width > window.innerWidth) {
    left = x - tooltipRect.width - 12;
  }
  if (top + tooltipRect.height > window.innerHeight) {
    top = y - tooltipRect.height - 12;
  }

  pickerState.tooltip.style.left = `${left}px`;
  pickerState.tooltip.style.top = `${top}px`;
}

// ---------------------------------------------------------------------------
// Activation / Deactivation
// ---------------------------------------------------------------------------

/**
 * Activate the visual selector picker on the page.
 */
export function activatePicker(): void {
  if (pickerState.active) return;

  injectPickerStyles();

  // Create overlay (captures pointer events notice)
  const overlay = document.createElement("div");
  overlay.id = PICKER_OVERLAY_ID;
  document.body.appendChild(overlay);
  pickerState.overlay = overlay;

  // Create tooltip
  const tooltip = document.createElement("div");
  tooltip.id = PICKER_TOOLTIP_ID;
  tooltip.style.display = "none";
  document.body.appendChild(tooltip);
  pickerState.tooltip = tooltip;

  pickerState.active = true;

  // Attach event listeners to document (capture phase for click)
  document.addEventListener("mousemove", onMouseMove, true);
  document.addEventListener("click", onClick, true);
  document.addEventListener("keydown", onKeyDown, true);
}

/**
 * Deactivate the selector picker and clean up.
 */
export function deactivatePicker(): void {
  if (!pickerState.active) return;

  pickerState.active = false;

  // Remove event listeners
  document.removeEventListener("mousemove", onMouseMove, true);
  document.removeEventListener("click", onClick, true);
  document.removeEventListener("keydown", onKeyDown, true);

  // Clean up hover highlight
  if (pickerState.hoveredElement) {
    pickerState.hoveredElement.classList.remove(PICKER_HIGHLIGHT_CLASS);
    pickerState.hoveredElement = null;
  }

  // Clean up selected highlights
  for (const el of pickerState.selectedElements) {
    el.classList.remove(PICKER_SELECTED_CLASS);
  }
  pickerState.selectedElements = [];

  // Remove overlay and tooltip
  pickerState.overlay?.remove();
  pickerState.overlay = null;
  pickerState.tooltip?.remove();
  pickerState.tooltip = null;

  // Notify popup that picker was deactivated
  chrome.runtime.sendMessage({ action: "selectorPickerStopped" });
}

/**
 * Check if the picker is currently active.
 */
export function isPickerActive(): boolean {
  return pickerState.active;
}

// ---------------------------------------------------------------------------
// Message listener (activated from background/popup)
// ---------------------------------------------------------------------------

if (typeof chrome !== "undefined" && chrome.runtime) {
  chrome.runtime.onMessage.addListener(
    (message: any, _sender: any, sendResponse: any) => {
      if (message.action === "activateSelectorPicker") {
        activatePicker();
        sendResponse({ active: true });
        return false;
      }

      if (message.action === "deactivateSelectorPicker") {
        deactivatePicker();
        sendResponse({ active: false });
        return false;
      }

      if (message.action === "isPickerActive") {
        sendResponse({ active: pickerState.active });
        return false;
      }

      return false;
    }
  );
}
