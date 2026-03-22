/**
 * AI Scraper — Client-Side Extraction Service
 *
 * Extracts structured data from the current page DOM using CSS selectors,
 * XPath expressions, and automatic detection. Returns results matching
 * the Result contract from packages/contracts.
 *
 * This module is designed to run in a content script context where it
 * has access to the page DOM.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExtractionResult {
  url: string;
  timestamp: string;
  extraction_method: string;
  confidence: number;
  data: Record<string, unknown>;
  metadata: PageMetadata;
  items: ExtractedItem[];
}

export interface ExtractedItem {
  selector: string;
  type: "css" | "xpath";
  value: string | string[];
  element_tag?: string;
  element_count: number;
}

export interface PageMetadata {
  url: string;
  title: string;
  description: string;
  canonical_url: string;
  og: Record<string, string>;
  json_ld: unknown[];
  detected_type: string;
  language: string;
  charset: string;
}

export interface ExtractionConfig {
  selectors: SelectorRule[];
  mode?: string;
  include_metadata?: boolean;
  max_items?: number;
}

export interface SelectorRule {
  name: string;
  selector: string;
  type: "css" | "xpath";
  attribute?: string;
  multiple?: boolean;
  transform?: "text" | "html" | "attribute" | "href" | "src";
}

// ---------------------------------------------------------------------------
// CSS Selector Extraction
// ---------------------------------------------------------------------------

/**
 * Extract data from the page using a CSS selector.
 * Returns text content of matched elements.
 */
export function extractByCSS(
  selector: string,
  attribute?: string,
  multiple: boolean = true
): string | string[] | null {
  try {
    if (multiple) {
      const elements = document.querySelectorAll(selector);
      if (elements.length === 0) return null;
      return Array.from(elements).map((el) =>
        attribute ? el.getAttribute(attribute) || "" : el.textContent?.trim() || ""
      );
    } else {
      const element = document.querySelector(selector);
      if (!element) return null;
      return attribute
        ? element.getAttribute(attribute) || ""
        : element.textContent?.trim() || "";
    }
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// XPath Extraction
// ---------------------------------------------------------------------------

/**
 * Extract data from the page using an XPath expression.
 * Returns text content of matched nodes.
 */
export function extractByXPath(
  expression: string,
  multiple: boolean = true
): string | string[] | null {
  try {
    const resultType = multiple
      ? XPathResult.ORDERED_NODE_SNAPSHOT_TYPE
      : XPathResult.FIRST_ORDERED_NODE_TYPE;

    const result = document.evaluate(
      expression,
      document,
      null,
      resultType,
      null
    );

    if (!multiple) {
      const node = result.singleNodeValue;
      if (!node) return null;
      return node.textContent?.trim() || "";
    }

    const values: string[] = [];
    for (let i = 0; i < result.snapshotLength; i++) {
      const node = result.snapshotItem(i);
      if (node) {
        values.push(node.textContent?.trim() || "");
      }
    }
    return values.length > 0 ? values : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Combined extraction
// ---------------------------------------------------------------------------

/**
 * Execute a full extraction based on the provided configuration.
 * Applies all selector rules and returns structured results.
 */
export function extractAll(config: ExtractionConfig): ExtractionResult {
  const metadata = config.include_metadata !== false ? getPageMetadata() : {
    url: location.href,
    title: document.title,
    description: "",
    canonical_url: "",
    og: {},
    json_ld: [],
    detected_type: "unknown",
    language: "",
    charset: "",
  };

  const items: ExtractedItem[] = [];
  const data: Record<string, unknown> = {};
  let successCount = 0;

  const maxItems = config.max_items || 100;

  for (const rule of config.selectors) {
    let value: string | string[] | null;

    if (rule.type === "xpath") {
      value = extractByXPath(rule.selector, rule.multiple !== false);
    } else {
      value = extractByCSS(
        rule.selector,
        rule.attribute || (rule.transform === "href" ? "href" : rule.transform === "src" ? "src" : undefined),
        rule.multiple !== false
      );
    }

    if (value !== null) {
      successCount++;

      // Apply transform for html extraction
      if (rule.transform === "html" && rule.type === "css") {
        const elements = document.querySelectorAll(rule.selector);
        value = Array.from(elements)
          .slice(0, maxItems)
          .map((el) => (el as HTMLElement).innerHTML);
        if (!rule.multiple && value.length > 0) {
          value = value[0];
        }
      }

      // Limit array results
      if (Array.isArray(value)) {
        value = value.slice(0, maxItems);
      }
    }

    data[rule.name] = value;

    const elementCount = rule.type === "css"
      ? document.querySelectorAll(rule.selector).length
      : countXPathResults(rule.selector);

    items.push({
      selector: rule.selector,
      type: rule.type,
      value: value || (rule.multiple !== false ? [] : ""),
      element_tag: getFirstElementTag(rule.selector, rule.type),
      element_count: elementCount,
    });
  }

  // Calculate confidence based on how many selectors matched
  const confidence =
    config.selectors.length > 0
      ? successCount / config.selectors.length
      : 0;

  return {
    url: location.href,
    timestamp: new Date().toISOString(),
    extraction_method: config.mode || "selector",
    confidence,
    data,
    metadata,
    items,
  };
}

// ---------------------------------------------------------------------------
// Page metadata extraction
// ---------------------------------------------------------------------------

/**
 * Extract comprehensive metadata about the current page.
 */
export function getPageMetadata(): PageMetadata {
  // Open Graph tags
  const og: Record<string, string> = {};
  document.querySelectorAll('meta[property^="og:"]').forEach((tag) => {
    const property = tag.getAttribute("property");
    const content = tag.getAttribute("content");
    if (property && content) {
      og[property.replace("og:", "")] = content;
    }
  });

  // JSON-LD
  const jsonLd: unknown[] = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach((script) => {
    try {
      jsonLd.push(JSON.parse(script.textContent || ""));
    } catch {
      // skip malformed
    }
  });

  // Description
  const descriptionEl =
    document.querySelector('meta[name="description"]') ||
    document.querySelector('meta[property="og:description"]');
  const description = descriptionEl?.getAttribute("content") || "";

  // Canonical URL
  const canonicalEl = document.querySelector('link[rel="canonical"]');
  const canonicalUrl = canonicalEl?.getAttribute("href") || "";

  // Detect page type from JSON-LD
  const ldTypes = jsonLd.flatMap((ld: any) => {
    const t = ld?.["@type"];
    return Array.isArray(t) ? t : t ? [t] : [];
  });
  let detectedType = "unknown";
  const typeStr = ldTypes.join(" ").toLowerCase();
  if (typeStr.includes("product")) detectedType = "product";
  else if (typeStr.includes("article") || typeStr.includes("news")) detectedType = "article";
  else if (typeStr.includes("itemlist")) detectedType = "listing";

  // Language
  const language =
    document.documentElement.getAttribute("lang") ||
    document.querySelector('meta[http-equiv="content-language"]')?.getAttribute("content") ||
    "";

  // Charset
  const charsetMeta = document.querySelector('meta[charset]');
  const charset = charsetMeta?.getAttribute("charset") || "UTF-8";

  return {
    url: location.href,
    title: document.title,
    description,
    canonical_url: canonicalUrl,
    og,
    json_ld: jsonLd,
    detected_type: detectedType,
    language,
    charset,
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function countXPathResults(expression: string): number {
  try {
    const result = document.evaluate(
      expression,
      document,
      null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
      null
    );
    return result.snapshotLength;
  } catch {
    return 0;
  }
}

function getFirstElementTag(selector: string, type: "css" | "xpath"): string | undefined {
  try {
    if (type === "css") {
      const el = document.querySelector(selector);
      return el?.tagName?.toLowerCase();
    } else {
      const result = document.evaluate(
        selector,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      const node = result.singleNodeValue;
      return (node as Element)?.tagName?.toLowerCase();
    }
  } catch {
    return undefined;
  }
}
