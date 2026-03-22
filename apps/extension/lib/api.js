/**
 * AI Scraper — API Client
 *
 * Communicates with the control plane for cloud-based extraction
 * and AI normalization.
 */

/**
 * Send extracted data to the control plane for processing.
 *
 * @param {object} options
 * @param {string} options.endpoint  Base URL of the control plane
 * @param {string} options.apiKey    Bearer token
 * @param {object} options.payload   Request body ({ url, mode, raw })
 * @returns {Promise<object>}        Normalized extraction result
 */
export async function sendToControlPlane({ endpoint, apiKey, payload }) {
  const url = `${endpoint.replace(/\/+$/, "")}/api/v1/extract`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Control plane error ${response.status}: ${text}`);
  }

  return response.json();
}

/**
 * Check control plane health.
 *
 * @param {string} endpoint  Base URL
 * @returns {Promise<boolean>}
 */
export async function checkHealth(endpoint) {
  try {
    const url = `${endpoint.replace(/\/+$/, "")}/health`;
    const response = await fetch(url, { method: "GET" });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Fetch available extraction policies from the control plane.
 *
 * @param {string} endpoint
 * @param {string} apiKey
 * @returns {Promise<object[]>}
 */
export async function fetchPolicies(endpoint, apiKey) {
  const url = `${endpoint.replace(/\/+$/, "")}/api/v1/policies`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch policies: ${response.status}`);
  }

  return response.json();
}
