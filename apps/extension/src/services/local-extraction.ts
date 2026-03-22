/**
 * Local Extraction Service — routes extraction requests through the native
 * messaging host to the local companion / control plane.
 *
 * Fallback strategy:
 *   1. Local companion (via native messaging)
 *   2. Cloud control plane (via HTTP API)
 *   3. Offline queue (persisted in chrome.storage.local for later retry)
 */

import {
  nativeMessaging,
  NativeResponse,
} from "./native-messaging.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExtractionConfig {
  url: string;
  mode?: string;
  taskType?: string;
  metadata?: Record<string, unknown>;
  html?: string;
}

export interface ExtractionResult {
  success: boolean;
  source: "local" | "cloud" | "offline_queued";
  data?: unknown;
  taskId?: string;
  error?: string;
}

export interface LocalStatus {
  companion: boolean;
  server: boolean;
  version?: string;
}

// ---------------------------------------------------------------------------
// Cloud fallback helpers
// ---------------------------------------------------------------------------

async function getSettings(): Promise<{
  apiEndpoint: string;
  apiKey: string;
  useCloud: boolean;
}> {
  const defaults = {
    apiEndpoint: "http://localhost:8000",
    apiKey: "",
    useCloud: false,
  };
  const stored = await chrome.storage.local.get(Object.keys(defaults));
  return { ...defaults, ...stored } as typeof defaults;
}

async function cloudExtract(
  config: ExtractionConfig,
  settings: { apiEndpoint: string; apiKey: string }
): Promise<ExtractionResult> {
  const endpoint = settings.apiEndpoint.replace(/\/+$/, "");
  const url = `${endpoint}/api/v1/tasks`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(settings.apiKey
        ? { Authorization: `Bearer ${settings.apiKey}` }
        : {}),
    },
    body: JSON.stringify({
      url: config.url,
      task_type: config.taskType ?? "scrape",
      metadata: config.metadata ?? {},
    }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Cloud API error ${response.status}: ${text}`);
  }

  const data = await response.json();
  return { success: true, source: "cloud", data, taskId: data.id };
}

// ---------------------------------------------------------------------------
// Offline queue
// ---------------------------------------------------------------------------

async function enqueueOffline(config: ExtractionConfig): Promise<void> {
  const key = "offline_queue";
  const stored = await chrome.storage.local.get(key);
  const queue: ExtractionConfig[] = stored[key] ?? [];
  queue.push({ ...config, metadata: { ...config.metadata, queued_at: new Date().toISOString() } });
  await chrome.storage.local.set({ [key]: queue });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Execute an extraction via the local companion if available, falling back
 * to cloud, then offline queue.
 */
export async function executeLocal(
  config: ExtractionConfig
): Promise<ExtractionResult> {
  // 1. Try local companion
  if (nativeMessaging.isConnected()) {
    try {
      const response: NativeResponse = await nativeMessaging.sendMessage(
        "execute_task",
        {
          url: config.url,
          task_type: config.taskType ?? "scrape",
          mode: config.mode ?? "auto",
          metadata: config.metadata ?? {},
          html: config.html,
        }
      );

      if (response.success) {
        return {
          success: true,
          source: "local",
          data: response.payload,
          taskId:
            typeof response.payload === "object" && response.payload !== null
              ? (response.payload as Record<string, unknown>).task_id as string | undefined
              : undefined,
        };
      }

      // Local companion returned an error — fall through to cloud
      console.warn("[LocalExtraction] Companion error:", response.error);
    } catch (err) {
      console.warn("[LocalExtraction] Companion unreachable:", err);
    }
  }

  // 2. Try cloud
  const settings = await getSettings();
  if (settings.useCloud && settings.apiKey) {
    try {
      return await cloudExtract(config, settings);
    } catch (err) {
      console.warn("[LocalExtraction] Cloud fallback failed:", err);
    }
  }

  // 3. Queue for later
  try {
    await enqueueOffline(config);
    return {
      success: false,
      source: "offline_queued",
      error: "Both local and cloud unavailable — queued for later",
    };
  } catch (err) {
    return {
      success: false,
      source: "offline_queued",
      error: `Failed to queue: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * Check local companion and control plane status.
 */
export async function getLocalStatus(): Promise<LocalStatus> {
  const companionConnected = nativeMessaging.isConnected();

  if (!companionConnected) {
    return { companion: false, server: false };
  }

  try {
    const response = await nativeMessaging.sendMessage("health_check", {});
    return {
      companion: true,
      server: response.success,
      version:
        typeof response.payload === "object" && response.payload !== null
          ? (response.payload as Record<string, unknown>).version as string | undefined
          : undefined,
    };
  } catch {
    return { companion: true, server: false };
  }
}

/**
 * Fetch results for a specific task from the local control plane.
 */
export async function getLocalResults(
  taskId: string
): Promise<ExtractionResult> {
  if (!nativeMessaging.isConnected()) {
    return {
      success: false,
      source: "local",
      error: "Companion not connected",
    };
  }

  try {
    const response = await nativeMessaging.sendMessage("get_results", {
      task_id: taskId,
    });

    return {
      success: response.success,
      source: "local",
      data: response.payload,
      taskId,
      error: response.error,
    };
  } catch (err) {
    return {
      success: false,
      source: "local",
      taskId,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
