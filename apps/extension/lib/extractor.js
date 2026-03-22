/**
 * AI Scraper — Client-Side Extractor Library
 *
 * Shared extraction utilities for JSON-LD, meta tags, and basic
 * schema.org markup.  This module is designed to work both in
 * content-script context (with a real DOM) and as a standalone
 * library when passed a parsed document.
 */

/**
 * Parse all JSON-LD script blocks from a document.
 *
 * @param {Document} doc
 * @returns {object[]}
 */
export function parseJsonLd(doc) {
  const blocks = doc.querySelectorAll('script[type="application/ld+json"]');
  const results = [];
  blocks.forEach((block) => {
    try {
      const parsed = JSON.parse(block.textContent);
      results.push(parsed);
    } catch {
      // skip malformed
    }
  });
  return results;
}

/**
 * Extract Open Graph and standard meta tags.
 *
 * @param {Document} doc
 * @returns {Record<string, string>}
 */
export function parseMeta(doc) {
  const meta = {};
  doc.querySelectorAll("meta[property], meta[name]").forEach((tag) => {
    const key = tag.getAttribute("property") || tag.getAttribute("name");
    const value = tag.getAttribute("content");
    if (key && value) {
      meta[key] = value;
    }
  });
  return meta;
}

/**
 * Extract microdata (itemscope/itemprop) into a flat map.
 *
 * @param {Document} doc
 * @returns {Record<string, string>}
 */
export function parseMicrodata(doc) {
  const data = {};
  doc.querySelectorAll("[itemprop]").forEach((el) => {
    const prop = el.getAttribute("itemprop");
    const value =
      el.getAttribute("content") ||
      el.getAttribute("href") ||
      el.getAttribute("src") ||
      el.textContent.trim();
    if (prop && value) {
      data[prop] = value;
    }
  });
  return data;
}

/**
 * Detect the likely page type from structured data.
 *
 * @param {object[]} jsonLd
 * @param {Record<string, string>} meta
 * @returns {"product" | "article" | "listing" | "unknown"}
 */
export function detectPageType(jsonLd, meta) {
  const ldTypes = jsonLd.flatMap((ld) => {
    const t = ld["@type"];
    return Array.isArray(t) ? t : t ? [t] : [];
  });

  const typeStr = ldTypes.join(" ").toLowerCase();
  const ogType = (meta["og:type"] || "").toLowerCase();

  if (typeStr.includes("product") || ogType === "product") return "product";
  if (typeStr.includes("article") || typeStr.includes("news") || ogType === "article") return "article";
  if (typeStr.includes("itemlist") || typeStr.includes("collection")) return "listing";

  return "unknown";
}

/**
 * Run all extractors and return a combined structured result.
 *
 * @param {Document} doc
 * @returns {object}
 */
export function extractAll(doc) {
  const jsonLd = parseJsonLd(doc);
  const meta = parseMeta(doc);
  const microdata = parseMicrodata(doc);
  const pageType = detectPageType(jsonLd, meta);

  return {
    url: doc.location?.href || "",
    pageType,
    jsonLd,
    meta,
    microdata,
    title: doc.title || "",
    timestamp: new Date().toISOString(),
  };
}
