/**
 * AI Scraper — Background Cloud Sync Service
 *
 * Compiled from src/background/cloud-sync.ts
 * Periodic health checks, task status polling, offline queue management.
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const HEALTH_CHECK_INTERVAL_MS = 30000;
const TASK_POLL_INTERVAL_MS = 10000;
const QUEUE_FLUSH_INTERVAL_MS = 15000;
const MAX_QUEUE_SIZE = 50;
const MAX_TASK_POLL_COUNT = 360;
const MAX_RETRY_COUNT = 5;
const QUEUE_STORAGE_KEY = "cloudSyncQueue";
const WATCHES_STORAGE_KEY = "cloudSyncWatches";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const syncState = {
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

async function persistQueue() {
  await chrome.storage.local.set({ [QUEUE_STORAGE_KEY]: syncState.offlineQueue });
}

async function persistWatches() {
  await chrome.storage.local.set({ [WATCHES_STORAGE_KEY]: syncState.watchedTasks });
}

async function loadPersistedState() {
  const stored = await chrome.storage.local.get([QUEUE_STORAGE_KEY, WATCHES_STORAGE_KEY]);
  if (Array.isArray(stored[QUEUE_STORAGE_KEY])) {
    syncState.offlineQueue = stored[QUEUE_STORAGE_KEY];
  }
  if (Array.isArray(stored[WATCHES_STORAGE_KEY])) {
    syncState.watchedTasks = stored[WATCHES_STORAGE_KEY];
  }
}

async function getCloudConfig() {
  const stored = await chrome.storage.local.get(["apiEndpoint", "apiKey", "useCloud"]);
  return {
    baseUrl: (stored.apiEndpoint || "http://localhost:8000").replace(/\/+$/, ""),
    apiKey: stored.apiKey || "",
    useCloud: stored.useCloud || false,
  };
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

async function checkHealth() {
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

async function pollWatchedTasks() {
  if (!syncState.connected || syncState.watchedTasks.length === 0) return;

  const config = await getCloudConfig();
  const completedIndices = [];

  for (let i = 0; i < syncState.watchedTasks.length; i++) {
    const watch = syncState.watchedTasks[i];
    watch.pollCount++;

    if (watch.pollCount > MAX_TASK_POLL_COUNT) {
      completedIndices.push(i);
      continue;
    }

    try {
      const response = await fetch(
        `${config.baseUrl}/api/v1/tasks/${watch.taskId}`,
        {
          headers: { Authorization: `Bearer ${config.apiKey}` },
          signal: AbortSignal.timeout(5000),
        }
      );

      if (!response.ok) continue;

      const task = await response.json();
      const prevStatus = watch.lastStatus;
      watch.lastStatus = task.status;

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
      // Skip this cycle
    }
  }

  for (let i = completedIndices.length - 1; i >= 0; i--) {
    syncState.watchedTasks.splice(completedIndices[i], 1);
  }

  await persistWatches();
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

function notifyTaskComplete(taskId) {
  if (chrome.notifications) {
    chrome.notifications.create(`task-complete-${taskId}`, {
      type: "basic",
      iconUrl: chrome.runtime.getURL("icons/icon128.png"),
      title: "Extraction Complete",
      message: `Task ${taskId.substring(0, 8)}... has finished.`,
    });
  }
  chrome.runtime.sendMessage({
    action: "taskStatusChanged",
    taskId,
    status: "completed",
  }).catch(() => {});
}

function notifyTaskFailed(taskId) {
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

export function enqueue(action, payload) {
  const id = `q_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const request = {
    id,
    action,
    payload,
    timestamp: Date.now(),
    retries: 0,
    maxRetries: MAX_RETRY_COUNT,
  };

  if (syncState.offlineQueue.length >= MAX_QUEUE_SIZE) {
    syncState.offlineQueue.shift();
  }

  syncState.offlineQueue.push(request);
  persistQueue();
  return id;
}

async function flushQueue() {
  if (!syncState.connected || syncState.offlineQueue.length === 0) return;

  const config = await getCloudConfig();
  const processed = [];

  for (let i = 0; i < syncState.offlineQueue.length; i++) {
    const request = syncState.offlineQueue[i];

    try {
      let url;
      let body;

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
          processed.push(i);
          continue;
      }

      const response = await fetch(url, {
        method: "POST",
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
        processed.push(i);
      } else {
        request.retries++;
        if (request.retries >= request.maxRetries) processed.push(i);
      }
    } catch {
      request.retries++;
      if (request.retries >= request.maxRetries) processed.push(i);
      break;
    }
  }

  for (let i = processed.length - 1; i >= 0; i--) {
    syncState.offlineQueue.splice(processed[i], 1);
  }

  await persistQueue();
}

// ---------------------------------------------------------------------------
// Task watching
// ---------------------------------------------------------------------------

export function watchTask(taskId) {
  if (syncState.watchedTasks.some((w) => w.taskId === taskId)) return;
  syncState.watchedTasks.push({
    taskId,
    lastStatus: "pending",
    pollCount: 0,
    createdAt: Date.now(),
  });
  persistWatches();
}

export function unwatchTask(taskId) {
  syncState.watchedTasks = syncState.watchedTasks.filter((w) => w.taskId !== taskId);
  persistWatches();
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

export async function startCloudSync() {
  await loadPersistedState();
  await checkHealth();

  syncState.healthCheckInterval = setInterval(checkHealth, HEALTH_CHECK_INTERVAL_MS);
  syncState.taskPollInterval = setInterval(pollWatchedTasks, TASK_POLL_INTERVAL_MS);
  syncState.queueFlushInterval = setInterval(flushQueue, QUEUE_FLUSH_INTERVAL_MS);

  chrome.storage.onChanged.addListener((changes) => {
    if (changes.useCloud?.newValue === true || changes.apiKey?.newValue) {
      checkHealth().then((connected) => {
        if (connected) flushQueue();
      });
    }
  });
}

export function stopCloudSync() {
  if (syncState.healthCheckInterval) clearInterval(syncState.healthCheckInterval);
  if (syncState.taskPollInterval) clearInterval(syncState.taskPollInterval);
  if (syncState.queueFlushInterval) clearInterval(syncState.queueFlushInterval);
  syncState.healthCheckInterval = null;
  syncState.taskPollInterval = null;
  syncState.queueFlushInterval = null;
}

export function getSyncStatus() {
  return {
    connected: syncState.connected,
    lastHealthCheck: syncState.lastHealthCheck,
    latency: syncState.lastLatency,
    queueSize: syncState.offlineQueue.length,
    watchedTaskCount: syncState.watchedTasks.length,
  };
}

// ---------------------------------------------------------------------------
// Message handler
// ---------------------------------------------------------------------------

export function handleCloudSyncMessage(message, _sender, sendResponse) {
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
      checkHealth().then((connected) => sendResponse({ connected }));
      return true;

    case "flushQueue":
      flushQueue().then(() =>
        sendResponse({ flushed: true, remaining: syncState.offlineQueue.length })
      );
      return true;

    case "sendToCloud": {
      if (syncState.connected) {
        getCloudConfig().then(async (config) => {
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
              sendResponse({ success: false, error: `Cloud error ${response.status}: ${text}` });
            }
          } catch {
            enqueue("sendExtraction", { url: message.url, mode: message.mode, data: message.data });
            sendResponse({ success: false, error: "Request queued for retry", queued: true });
          }
        });
        return true;
      } else {
        const queueId = enqueue("sendExtraction", {
          url: message.url,
          mode: message.mode,
          data: message.data,
        });
        sendResponse({ success: false, error: "Cloud offline — request queued", queued: true, queueId });
        return false;
      }
    }

    default:
      return false;
  }
}
