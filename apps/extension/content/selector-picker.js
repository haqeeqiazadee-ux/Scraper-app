/**
 * AI Scraper — Visual Selector Picker (Content Script)
 *
 * Compiled from src/services/selector-picker.ts
 * Injects into the page to let users visually select elements
 * and generate optimal CSS selectors.
 */

(() => {
  "use strict";

  // Prevent double-injection
  if (window.__aiScraperPickerInjected) return;
  window.__aiScraperPickerInjected = true;

  // -------------------------------------------------------------------------
  // Constants
  // -------------------------------------------------------------------------

  const PICKER_HIGHLIGHT_CLASS = "ai-scraper-picker-highlight";
  const PICKER_SELECTED_CLASS = "ai-scraper-picker-selected";
  const PICKER_TOOLTIP_ID = "ai-scraper-picker-tooltip";

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  let active = false;
  let hoveredElement = null;
  const selectedElements = [];
  let tooltip = null;

  // -------------------------------------------------------------------------
  // Style injection
  // -------------------------------------------------------------------------

  let stylesInjected = false;

  function injectStyles() {
    if (stylesInjected) return;
    stylesInjected = true;

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

  // -------------------------------------------------------------------------
  // Selector generation
  // -------------------------------------------------------------------------

  function escapeCSS(str) {
    if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(str);
    return str.replace(/([^\w-])/g, "\\$1");
  }

  function generateSelector(element) {
    // ID-based
    if (element.id) {
      return `#${escapeCSS(element.id)}`;
    }

    // Unique class
    const classSelector = getUniqueClassSelector(element);
    if (classSelector) return classSelector;

    // Attribute-based
    const attrSelector = getAttributeSelector(element);
    if (attrSelector) return attrSelector;

    // Path-based fallback
    return getPathSelector(element);
  }

  function getUniqueClassSelector(element) {
    if (!element.classList || element.classList.length === 0) return null;

    const tag = element.tagName.toLowerCase();

    for (const cls of element.classList) {
      if (cls.startsWith("ai-scraper-")) continue;
      const selector = `${tag}.${escapeCSS(cls)}`;
      try {
        if (document.querySelectorAll(selector).length === 1) return selector;
      } catch { continue; }
    }

    if (element.classList.length > 1) {
      const classStr = Array.from(element.classList)
        .filter((c) => !c.startsWith("ai-scraper-"))
        .map((c) => `.${escapeCSS(c)}`)
        .join("");
      if (classStr) {
        const selector = `${tag}${classStr}`;
        try {
          if (document.querySelectorAll(selector).length === 1) return selector;
        } catch { /* fall through */ }
      }
    }

    return null;
  }

  function getAttributeSelector(element) {
    const tag = element.tagName.toLowerCase();
    const attrs = ["data-testid", "data-id", "name", "role", "type", "aria-label"];

    for (const attr of attrs) {
      const value = element.getAttribute(attr);
      if (value) {
        const selector = `${tag}[${attr}="${escapeCSS(value)}"]`;
        try {
          if (document.querySelectorAll(selector).length === 1) return selector;
        } catch { continue; }
      }
    }

    return null;
  }

  function getPathSelector(element) {
    const parts = [];
    let current = element;

    while (current && current !== document.documentElement) {
      let selector = current.tagName.toLowerCase();

      if (current.id) {
        parts.unshift(`#${escapeCSS(current.id)}`);
        break;
      }

      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          (s) => s.tagName === current.tagName
        );
        if (siblings.length > 1) {
          const index = siblings.indexOf(current) + 1;
          selector += `:nth-child(${index})`;
        }
      }

      parts.unshift(selector);
      current = parent;

      if (parts.length >= 5) break;
    }

    return parts.join(" > ");
  }

  // -------------------------------------------------------------------------
  // Event handlers
  // -------------------------------------------------------------------------

  function onMouseMove(event) {
    if (!active) return;

    const target = document.elementFromPoint(event.clientX, event.clientY);
    if (!target || target === hoveredElement) return;

    if (hoveredElement) {
      hoveredElement.classList.remove(PICKER_HIGHLIGHT_CLASS);
    }

    if (target.id === PICKER_TOOLTIP_ID) return;

    hoveredElement = target;
    target.classList.add(PICKER_HIGHLIGHT_CLASS);
    updateTooltip(target, event.clientX, event.clientY);
  }

  function onClick(event) {
    if (!active) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    const target = hoveredElement;
    if (!target) return;

    const selector = generateSelector(target);
    const preview = (target.textContent || "").trim().substring(0, 100);

    target.classList.remove(PICKER_HIGHLIGHT_CLASS);
    target.classList.add(PICKER_SELECTED_CLASS);
    selectedElements.push(target);

    chrome.runtime.sendMessage({
      action: "selectorPicked",
      selector,
      preview,
      tag: target.tagName.toLowerCase(),
      elementCount: document.querySelectorAll(selector).length,
    });
  }

  function onKeyDown(event) {
    if (!active) return;
    if (event.key === "Escape") {
      deactivate();
    }
  }

  // -------------------------------------------------------------------------
  // Tooltip
  // -------------------------------------------------------------------------

  function updateTooltip(element, x, y) {
    if (!tooltip) return;

    const selector = generateSelector(element);
    const tag = element.tagName.toLowerCase();
    const classes = element.className && typeof element.className === "string"
      ? `.${Array.from(element.classList)
          .filter((c) => !c.startsWith("ai-scraper-"))
          .join(".")}`
      : "";

    tooltip.textContent = `${tag}${classes} → ${selector}`;
    tooltip.style.display = "block";

    let left = x + 12;
    let top = y + 12;
    const rect = tooltip.getBoundingClientRect();

    if (left + rect.width > window.innerWidth) left = x - rect.width - 12;
    if (top + rect.height > window.innerHeight) top = y - rect.height - 12;

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  // -------------------------------------------------------------------------
  // Activation / Deactivation
  // -------------------------------------------------------------------------

  function activate() {
    if (active) return;
    injectStyles();

    tooltip = document.createElement("div");
    tooltip.id = PICKER_TOOLTIP_ID;
    tooltip.style.display = "none";
    document.body.appendChild(tooltip);

    active = true;

    document.addEventListener("mousemove", onMouseMove, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKeyDown, true);
  }

  function deactivate() {
    if (!active) return;
    active = false;

    document.removeEventListener("mousemove", onMouseMove, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("keydown", onKeyDown, true);

    if (hoveredElement) {
      hoveredElement.classList.remove(PICKER_HIGHLIGHT_CLASS);
      hoveredElement = null;
    }

    for (const el of selectedElements) {
      el.classList.remove(PICKER_SELECTED_CLASS);
    }
    selectedElements.length = 0;

    if (tooltip) {
      tooltip.remove();
      tooltip = null;
    }

    chrome.runtime.sendMessage({ action: "selectorPickerStopped" });
  }

  // -------------------------------------------------------------------------
  // Message listener
  // -------------------------------------------------------------------------

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.action === "activateSelectorPicker") {
      activate();
      sendResponse({ active: true });
      return false;
    }

    if (message.action === "deactivateSelectorPicker") {
      deactivate();
      sendResponse({ active: false });
      return false;
    }

    if (message.action === "isPickerActive") {
      sendResponse({ active });
      return false;
    }

    return false;
  });
})();
