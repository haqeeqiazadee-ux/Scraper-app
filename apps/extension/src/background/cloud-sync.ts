/**
 * AI Scraper — Background Cloud Sync Service
 *
 * Runs in the background service worker context. Provides:
 * - Periodic health checks of the cloud control plane
 * - Status polling for running tasks
 * - Result notifications when tasks complete
 * - Offline queue for requests made when cloud is unreachable
 * - Automatic retry with exponential backoff
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QueuedRequest {
  id: string;
  action: string;
  payload: Record<string, unknown>;
  timestamp: number;
  retries: number;
  maxRetries: number;
}

interface TaskWatch {
  taskId: string;
  lastStatus: string;
  pollCount: number;
  createdAt: number;
}

interface CloudSyncState {
  connected: boolean;
  lastHealthCheck: number;
  lastLatency: number;
  offlineQueue: QueuedRequest[];
  watchedTasks: TaskWatch[];
  healthCheckInterval: ReturnType<typeof setInterval> | null;
  taskPollInterval: ReturnType<typeof setInterval> | null;
  queueFlushInterval: ReturnType<typeof setInterval> | null;
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const HEALTH_CHECK_INTERVAL_MS = 30_000;    // 30 seconds
const TASK_POLL_INTERVAL_MS = 10_000;       // 10 seconds
const QUEUE_FLUSH_INTERVAL_MS = 15_000;     // 15 seconds
const MAX_QUEUE_SIZE = 50;
const MAX_TASK_POLL_COUNT = 360;            // ~1 hour at 10s intervals
const MAX_RETRY_COUNT = 5;
const QUEUE_STORAGE_KEY = "cloudSyncQueue";
const WATCHES_STORAGE_KEY = "cloudSyncWatches";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const syncState: CloudSyncState = {
  connected: false,
  lastHealthCheck: 0,
  lastLatency: 0,
  offlineQueue: [],
  watchedTasks: [],
  healthCheckInterval: null,
  taskPollInterval: null,
  queueFlushInterval: null,
};

// ---------------------------------------------------------------------------
// Storage persistence
// ---------------------------------------------------------------------------

async function persistQueue(): Promise<void> {
  await chrome.storage.local.set({
    [QUEUE_STORAGE_KEY]: syncState.offlineQueue,
  });
}

async function persistWatches(): Promise<void> {
  await chrome.storage.local.set({
    [WATCHES_STORAGE_KEY]: syncState.watchedTasks,
  });
}

async function loadPersistedState(): Promise<void> {
  const stored = await chrome.storage.local.get([
    QUEUE_STORAGE_KEY,
    WATCHES_STORAGE_KEY,
  ]);
  if (Array.isArray(stored[QUEUE_STORAGE_KEY])) {
    syncState.offlineQueue = stored[QUEUE_STORAGE_KEY];
  }
  if (Array.isArray(stored[WATCHES_STORAGE_KEY])) {
    syncState.watchedTasks = stored[WATCHES_STORAGE_KEY];
  }
}

// ---------------------------------------------------------------------------
// Settings helper
// ---------------------------------------------------------------------------

async function getCloudConfig(): Promise<{ baseUrl: string; apiKey: string; useCloud: boolean }> {
  const defaults = {
    apiEndpoint: "http://localhost:8000",
    apiKey: "",
    useCloud: false,
  };
  const stored = await chrome.storage.local.get(["apiEndpoint", "apiKey", "useCloud"]);
  return {
    baseUrl: ((stored.apiEndpoint as string) || defaults.apiEndpoint).replace(/\/+$/, ""),
    apiKey: (stored.apiKey as string) || defaults.apiKey,
    useCloud: (stored.useCloud as boolean) || false,
  };
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

async function checkHealth(): Promise<boolean> {
  const config = await getCloudConfig();
  if (!config.useCloud || !config.apiKey) {
    syncState.connected = false;
    return false;
  }

  const start = Date.now();
  try {
    const response = await fetch(`${config.baseUrl}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    });
    syncState.lastLatency = Date.now() - start;
    syncState.connected = response.ok;
    syncState.lastHealthCheck = Date.now();
  } catch {
    syncState.lastLatency = Date.now() - start;
    syncState.connected = false;
    syncState.lastHealthCheck = Date.now();
  }

  return syncState.connected;
}

// ---------------------------------------------------------------------------
// Task polling
// ---------------------------------------------------------------------------

async function pollWatchedTasks(): Promise<void> {
  if (!syncState.connected || syncState.watchedTasks.length === 0) return;

  const config = await getCloudConfig();
  const completedIndices: number[] = [];

  for (let i = 0; i < syncState.watchedTasks.length; i++) {
    const watch = syncState.watchedTasks[i];
    watch.pollCount++;

    // Stop polling after max attempts
    if (watch.pollCount > MAX_TASK_POLL_COUNT) {
      completedIndices.push(i);
      continue;
    }

    try {
      const response = await fetch(
        `${config.baseUrl}/api/v1/tasks/${watch.taskId}`,
        {
          headers: {
            Authorization: `Bearer ${config.apiKey}`,
          },
          signal: AbortSignal.timeout(5000),
        }
      );

      if (!response.ok) continue;

      const task = (await response.json()) as { status: string; id: string };
      const prevStatus = watch.lastStatus;
      watch.lastStatus = task.status;

      // Notify on status change
      if (prevStatus !== task.status) {
        if (task.status === "completed") {
          notifyTaskComplete(watch.taskId);
          completedIndices.push(i);
        } else if (task.status === "failed") {
          notifyTaskFailed(watch.taskId);
          completedIndices.push(i);
        }
      }
    } catch {
      // Network error — skip this poll cycle
    }
  }

  // Remove completed/expired watches (iterate in reverse to maintain indices)
  for (let i = completedIndices.length - 1; i >= 0; i--) {
    syncState.watchedTasks.splice(completedIndices[i], 1);
  }

  await persistWatches();
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

function notifyTaskComplete(taskId: string): void {
  // Chrome extension notification
  if (chrome.notifications) {
    chrome.notifications.create(`task-complete-${taskId}`, {
      type: "basic",
      iconUrl: chrome.runtime.getURL("icons/icon128.png"),
      title: "Extraction Complete",
      message: `Task ${taskId.substring(0, 8)}... has finished. Click to view results.`,
    });
  }

  // Also broadcast to any open popups
  chrome.runtime.sendMessage({
    action: "taskStatusChanged",
    taskId,
    status: "completed",
  }).catch(() => {
    // Popup may not be open
  });
}

function notifyTaskFailed(taskId: string): void {
  if (chrome.notifications) {
    chrome.notifications.create(`task-failed-${taskId}`, {
      type: "basic",
      iconUrl: chrome.runtime.getURL("icons/icon128.png"),
      title: "Extraction Failed",
      message: `Task ${taskId.substring(0, 8)}... has failed.`,
    });
  }

  chrome.runtime.sendMessage({
    action: "taskStatusChanged",
    taskId,
    status: "failed",
  }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Offline queue
// ---------------------------------------------------------------------------

/**
 * Add a request to the offline queue.
 */
export function enqueue(action: string, payload: Record<string, unknown>): string {
  const id = `q_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const request: QueuedRequest = {
    id,
    action,
    payload,
    timestamp: Date.now(),
    retries: 0,
    maxRetries: MAX_RETRY_COUNT,
  };

  // Enforce queue size limit (drop oldest)
  if (syncState.offlineQueue.length >= MAX_QUEUE_SIZE) {
    syncState.offlineQueue.shift();
  }

  syncState.offlineQueue.push(request);
  persistQueue();
  return id;
}

/**
 * Flush queued requests when cloud becomes available.
 */
async function flushQueue(): Promise<void> {
  if (!syncState.connected || syncState.offlineQueue.length === 0) return;

  const config = await getCloudConfig();
  const processed: number[] = [];

  for (let i = 0; i < syncState.offlineQueue.length; i++) {
    const request = syncState.offlineQueue[i];

    try {
      let url: string;
      let method = "POST";
      let body: string | undefined;

      switch (request.action) {
        case "createTask":
          url = `${config.baseUrl}/api/v1/tasks`;
          body = JSON.stringify(request.payload);
          break;
        case "executeTask":
          url = `${config.baseUrl}/api/v1/tasks/${request.payload.taskId}/execute`;
          break;
        case "sendExtraction":
          url = `${config.baseUrl}/api/v1/extract`;
          body = JSON.stringify(request.payload);
          break;
        default:
          // Unknown action — discard
          processed.push(i);
          continue;
      }

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${config.apiKey}`,
        },
        body,
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        processed.push(i);
      } else if (response.status >= 400 && response.status < 500) {
        // Client error — don't retry
        processed.push(i);
      } else {
        // Server error — increment retry
        request.retries++;
        if (request.retries >= request.maxRetries) {
          processed.push(i);
        }
      }
    } catch {
      // Network error — increment retry
      request.retries++;
      if (request.retries >= request.maxRetries) {
        processed.push(i);
      }
      // Stop flushing on network error (likely still offline)
      break;
    }
  }

  // Remove processed items (reverse order)
  for (let i = processed.length - 1; i >= 0; i--) {
    syncState.offlineQueue.splice(processed[i], 1);
  }

  await persistQueue();
}

// ---------------------------------------------------------------------------
// Task watching
// ---------------------------------------------------------------------------

/**
 * Start watching a task for status changes.
 */
export function watchTask(taskId: string): void {
  // Don't duplicate watches
  if (syncState.watchedTasks.some((w) => w.taskId === taskId)) return;

  syncState.watchedTasks.push({
    taskId,
    lastStatus: "pending",
    pollCount: 0,
    createdAt: Date.now(),
  });

  persistWatches();
}

/**
 * Stop watching a task.
 */
export function unwatchTask(taskId: string): void {
  syncState.watchedTasks = syncState.watchedTasks.filter(
    (w) => w.taskId !== taskId
  );
  persistWatches();
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

/**
 * Start the cloud sync service. Call from service worker initialization.
 */
export async function startCloudSync(): Promise<void> {
  await loadPersistedState();

  // Initial health check
  await checkHealth();

  // Start periodic health checks
  syncState.healthCheckInterval = setInterval(
    checkHealth,
    HEALTH_CHECK_INTERVAL_MS
  );

  // Start task polling
  syncState.taskPollInterval = setInterval(
    pollWatchedTasks,
    TASK_POLL_INTERVAL_MS
  );

  // Start queue flushing
  syncState.queueFlushInterval = setInterval(
    flushQueue,
    QUEUE_FLUSH_INTERVAL_MS
  );

  // Attempt queue flush on reconnection
  chrome.storage.onChanged.addListener((changes) => {
    if (changes.useCloud?.newValue === true || changes.apiKey?.newValue) {
      checkHealth().then((connected) => {
        if (connected) flushQueue();
      });
    }
  });
}

/**
 * Stop the cloud sync service. Call on extension unload.
 */
export function stopCloudSync(): void {
  if (syncState.healthCheckInterval) {
    clearInterval(syncState.healthCheckInterval);
    syncState.healthCheckInterval = null;
  }
  if (syncState.taskPollInterval) {
    clearInterval(syncState.taskPollInterval);
    syncState.taskPollInterval = null;
  }
  if (syncState.queueFlushInterval) {
    clearInterval(syncState.queueFlushInterval);
    syncState.queueFlushInterval = null;
  }
}

/**
 * Get current sync status for display in popup.
 */
export function getSyncStatus(): {
  connected: boolean;
  lastHealthCheck: number;
  latency: number;
  queueSize: number;
  watchedTaskCount: number;
} {
  return {
    connected: syncState.connected,
    lastHealthCheck: syncState.lastHealthCheck,
    latency: syncState.lastLatency,
    queueSize: syncState.offlineQueue.length,
    watchedTaskCount: syncState.watchedTasks.length,
  };
}

// ---------------------------------------------------------------------------
// Message handler (called from service worker message router)
// ---------------------------------------------------------------------------

/**
 * Handle cloud-sync related messages from popup or content scripts.
 */
export function handleCloudSyncMessage(
  message: any,
  _sender: chrome.runtime.MessageSender,
  sendResponse: (response: any) => void
): boolean {
  switch (message.action) {
    case "cloudStatus":
      sendResponse(getSyncStatus());
      return false;

    case "watchTask":
      watchTask(message.taskId);
      sendResponse({ watching: true });
      return false;

    case "unwatchTask":
      unwatchTask(message.taskId);
      sendResponse({ watching: false });
      return false;

    case "getQueue":
      sendResponse({ queue: syncState.offlineQueue });
      return false;

    case "clearQueue":
      syncState.offlineQueue = [];
      persistQueue();
      sendResponse({ cleared: true });
      return false;

    case "forceHealthCheck":
      checkHealth().then((connected) => {
        sendResponse({ connected });
      });
      return true; // async response

    case "flushQueue":
      flushQueue().then(() => {
        sendResponse({
          flushed: true,
          remaining: syncState.offlineQueue.length,
        });
      });
      return true; // async response

    case "sendToCloud": {
      if (syncState.connected) {
        // Try direct send
        const config_promise = getCloudConfig();
        config_promise.then(async (config) => {
          try {
            const response = await fetch(`${config.baseUrl}/api/v1/extract`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${config.apiKey}`,
              },
              body: JSON.stringify({
                url: message.url,
                mode: message.mode || "auto",
                raw: message.data,
              }),
              signal: AbortSignal.timeout(30000),
            });
            if (response.ok) {
              const result = await response.json();
              sendResponse({ success: true, data: result });
            } else {
              const text = await response.text().catch(() => "");
              sendResponse({
                success: false,
                error: `Cloud error ${response.status}: ${text}`,
              });
            }
          } catch (err: unknown) {
            // Failed — queue for later
            enqueue("sendExtraction", {
              url: message.url,
              mode: message.mode,
              data: message.data,
            });
            sendResponse({
              success: false,
              error: "Request queued for retry",
              queued: true,
            });
          }
        });
        return true; // async
      } else {
        // Offline — queue
        const queueId = enqueue("sendExtraction", {
          url: message.url,
          mode: message.mode,
          data: message.data,
        });
        sendResponse({
          success: false,
          error: "Cloud offline — request queued",
          queued: true,
          queueId,
        });
        return false;
      }
    }

    default:
      return false;
  }
}
