/**
 * AI Scraper — Content Script
 *
 * Runs in the context of the visited page.  Extracts structured data
 * (JSON-LD, meta tags, Open Graph, basic DOM heuristics) and can
 * highlight extracted elements for visual feedback.
 */

(() => {
  "use strict";

  // Prevent double-injection
  if (window.__aiScraperInjected) return;
  window.__aiScraperInjected = true;

  // -------------------------------------------------------------------------
  // Highlight helpers
  // -------------------------------------------------------------------------

  const HIGHLIGHT_CLASS = "ai-scraper-highlight";

  const style = document.createElement("style");
  style.textContent = `
    .${HIGHLIGHT_CLASS} {
      outline: 2px solid #4f8cff !important;
      outline-offset: 2px;
      background: rgba(79, 140, 255, 0.08) !important;
      transition: outline-color 0.2s, background 0.2s;
    }
  `;
  document.head.appendChild(style);

  function highlightElements(selector) {
    clearHighlights();
    const els = document.querySelectorAll(selector);
    els.forEach((el) => el.classList.add(HIGHLIGHT_CLASS));
    return els.length;
  }

  function clearHighlights() {
    document.querySelectorAll(`.${HIGHLIGHT_CLASS}`).forEach((el) => {
      el.classList.remove(HIGHLIGHT_CLASS);
    });
  }

  // -------------------------------------------------------------------------
  // Extraction routines
  // -------------------------------------------------------------------------

  /** Extract all JSON-LD blocks from the page. */
  function extractJsonLd() {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    const results = [];
    scripts.forEach((s) => {
      try {
        results.push(JSON.parse(s.textContent));
      } catch {
        // skip malformed JSON-LD
      }
    });
    return results;
  }

  /** Extract Open Graph and standard meta tags. */
  function extractMeta() {
    const meta = {};
    const tags = document.querySelectorAll("meta[property], meta[name]");
    tags.forEach((tag) => {
      const key = tag.getAttribute("property") || tag.getAttribute("name");
      const value = tag.getAttribute("content");
      if (key && value) {
        meta[key] = value;
      }
    });
    return meta;
  }

  /** Basic product heuristics — price, title, images. */
  function extractProduct() {
    const title =
      document.querySelector("h1")?.textContent?.trim() ||
      document.title;

    const priceEl =
      document.querySelector('[class*="price" i]') ||
      document.querySelector('[itemprop="price"]');
    const price = priceEl ? priceEl.textContent.trim() : null;

    const images = Array.from(
      document.querySelectorAll("img[src]")
    )
      .map((img) => img.src)
      .filter((src) => src.startsWith("http"))
      .slice(0, 5);

    if (priceEl) highlightElements('[class*="price" i], [itemprop="price"]');

    return { title, price, images };
  }

  /** Extract listing items — repeated structures. */
  function extractListing() {
    // Heuristic: find the largest set of sibling elements sharing a tag+class.
    const candidates = new Map();
    document.querySelectorAll("ul > li, ol > li, [class*='item'], [class*='card']").forEach((el) => {
      const key = `${el.tagName}.${el.className}`;
      if (!candidates.has(key)) candidates.set(key, []);
      candidates.get(key).push(el);
    });

    let best = [];
    for (const group of candidates.values()) {
      if (group.length > best.length) best = group;
    }

    const items = best.slice(0, 50).map((el) => ({
      text: el.textContent.trim().substring(0, 300),
      links: Array.from(el.querySelectorAll("a[href]")).map((a) => ({
        text: a.textContent.trim(),
        href: a.href,
      })),
    }));

    return { count: items.length, items };
  }

  /** Extract article content. */
  function extractArticle() {
    const articleEl =
      document.querySelector("article") ||
      document.querySelector('[role="main"]') ||
      document.querySelector("main") ||
      document.body;

    const title =
      document.querySelector("h1")?.textContent?.trim() ||
      document.title;

    // Collect text from paragraphs inside the article container
    const paragraphs = Array.from(articleEl.querySelectorAll("p"))
      .map((p) => p.textContent.trim())
      .filter((t) => t.length > 20);

    if (articleEl !== document.body) {
      highlightElements("article, [role='main'], main");
    }

    return {
      title,
      paragraphs: paragraphs.slice(0, 50),
      wordCount: paragraphs.join(" ").split(/\s+/).length,
    };
  }

  /** Auto-detect the page type and run the best extractor. */
  function autoExtract() {
    const jsonLd = extractJsonLd();

    // Check JSON-LD types for hints
    const ldTypes = jsonLd.flatMap((ld) => {
      const t = ld["@type"];
      return Array.isArray(t) ? t : t ? [t] : [];
    });

    if (ldTypes.some((t) => /product/i.test(t))) {
      return { detectedMode: "product", ...extractProduct(), jsonLd };
    }
    if (ldTypes.some((t) => /article|news|blog/i.test(t))) {
      return { detectedMode: "article", ...extractArticle(), jsonLd };
    }

    // Fallback heuristic: if there's a price-like element, assume product
    if (document.querySelector('[class*="price" i], [itemprop="price"]')) {
      return { detectedMode: "product", ...extractProduct(), jsonLd };
    }

    // Default to article extraction
    return { detectedMode: "article", ...extractArticle(), jsonLd };
  }

  // -------------------------------------------------------------------------
  // Main extraction dispatcher
  // -------------------------------------------------------------------------

  function extract(mode) {
    const meta = extractMeta();
    const jsonLd = extractJsonLd();

    let modeData;
    switch (mode) {
      case "product":
        modeData = extractProduct();
        break;
      case "listing":
        modeData = extractListing();
        break;
      case "article":
        modeData = extractArticle();
        break;
      case "auto":
      default:
        modeData = autoExtract();
        break;
    }

    return {
      url: location.href,
      timestamp: new Date().toISOString(),
      mode,
      meta,
      jsonLd,
      ...modeData,
    };
  }

  // -------------------------------------------------------------------------
  // Message listener
  // -------------------------------------------------------------------------

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.action === "extract") {
      try {
        const data = extract(message.mode || "auto");
        sendResponse({ success: true, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
      return false;
    }

    if (message.action === "highlight") {
      const count = highlightElements(message.selector || "");
      sendResponse({ highlighted: count });
      return false;
    }

    if (message.action === "clearHighlights") {
      clearHighlights();
      sendResponse({ cleared: true });
      return false;
    }

    return false;
  });
})();
