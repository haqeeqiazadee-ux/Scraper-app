/**
 * Companion Bridge — background script that manages the native messaging
 * port lifecycle, monitors companion health, and routes messages between
 * popup/content scripts and the companion app.
 *
 * This module is imported by the service worker (background/service-worker.js)
 * and runs for the lifetime of the extension.
 */

import {
  nativeMessaging,
  NativeMessagingClient,
  NativeResponse,
} from "../services/native-messaging.js";
import { getLocalStatus, LocalStatus } from "../services/local-extraction.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** How often (ms) to check companion health. */
const HEALTH_CHECK_INTERVAL_MS = 30_000;

/** Connection state broadcasted to popup / options pages. */
export type ConnectionState = "local" | "cloud" | "offline";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let _healthTimer: ReturnType<typeof setInterval> | null = null;
let _lastStatus: LocalStatus = { companion: false, server: false };
let _connectionState: ConnectionState = "offline";

// ---------------------------------------------------------------------------
// Health monitoring
// ---------------------------------------------------------------------------

async function checkHealth(): Promise<void> {
  const status = await getLocalStatus();
  _lastStatus = status;

  const prevState = _connectionState;

  if (status.companion && status.server) {
    _connectionState = "local";
  } else {
    // Check cloud reachability
    try {
      const settings = await chrome.storage.local.get([
        "apiEndpoint",
        "apiKey",
        "useCloud",
      ]);
      if (settings.useCloud && settings.apiKey) {
        const endpoint = (settings.apiEndpoint || "http://localhost:8000").replace(/\/+$/, "");
        const resp = await fetch(`${endpoint}/health`, {
          method: "GET",
          signal: AbortSignal.timeout(5000),
        });
        _connectionState = resp.ok ? "cloud" : "offline";
      } else {
        _connectionState = "offline";
      }
    } catch {
      _connectionState = "offline";
    }
  }

  // Broadcast state change
  if (prevState !== _connectionState) {
    broadcastConnectionState();
  }
}

function broadcastConnectionState(): void {
  chrome.runtime.sendMessage({
    action: "connectionStateChanged",
    state: _connectionState,
    status: _lastStatus,
  }).catch(() => {
    // No receivers — popup may be closed, that's fine
  });
}

// ---------------------------------------------------------------------------
// Message routing — popup/content scripts ↔ companion
// ---------------------------------------------------------------------------

function handleBridgeMessage(
  message: Record<string, unknown>,
  _sender: chrome.runtime.MessageSender,
  sendResponse: (response: unknown) => void
): boolean {
  const action = message.action as string;

  // -- Connection state query --
  if (action === "getConnectionState") {
    sendResponse({
      state: _connectionState,
      status: _lastStatus,
      companionConnected: nativeMessaging.isConnected(),
    });
    return false;
  }

  // -- Forward to companion --
  if (action === "companionRequest") {
    const msgType = message.type as string;
    const payload = message.payload ?? {};

    if (!nativeMessaging.isConnected()) {
      sendResponse({ success: false, error: "Companion not connected" });
      return false;
    }

    nativeMessaging
      .sendMessage(msgType, payload)
      .then((resp: NativeResponse) => {
        sendResponse({
          success: resp.success,
          data: resp.payload,
          error: resp.error,
        });
      })
      .catch((err: Error) => {
        sendResponse({ success: false, error: err.message });
      });

    // Async response
    return true;
  }

  // -- Force reconnect --
  if (action === "reconnectCompanion") {
    nativeMessaging.disconnect();
    nativeMessaging.connect();
    sendResponse({ success: true });
    return false;
  }

  // -- Force health check --
  if (action === "checkHealth") {
    checkHealth()
      .then(() => {
        sendResponse({
          state: _connectionState,
          status: _lastStatus,
        });
      })
      .catch((err: Error) => {
        sendResponse({ error: err.message });
      });
    return true;
  }

  // Not handled by bridge
  return false;
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

/**
 * Start the companion bridge. Called once from the service worker on load.
 *
 * 1. Connects to the native messaging host.
 * 2. Starts a periodic health check.
 * 3. Registers a message listener for bridge-specific actions.
 */
export function startCompanionBridge(): void {
  // Connect to companion
  nativeMessaging.connect();

  // Listen for unsolicited messages from companion (e.g. push notifications)
  nativeMessaging.onMessage((msg: NativeResponse) => {
    if (msg.type === "companion_event") {
      // Forward companion events to any listening popup/content scripts
      chrome.runtime.sendMessage({
        action: "companionEvent",
        event: msg.payload,
      }).catch(() => {
        // No receivers
      });
    }
  });

  // Start health monitoring
  checkHealth();
  _healthTimer = setInterval(checkHealth, HEALTH_CHECK_INTERVAL_MS);

  // Register message handler
  chrome.runtime.onMessage.addListener(handleBridgeMessage);

  console.log("[CompanionBridge] Started");
}

/**
 * Stop the companion bridge. Disconnects native messaging and clears timers.
 */
export function stopCompanionBridge(): void {
  if (_healthTimer) {
    clearInterval(_healthTimer);
    _healthTimer = null;
  }

  nativeMessaging.disconnect();
  chrome.runtime.onMessage.removeListener(handleBridgeMessage);

  console.log("[CompanionBridge] Stopped");
}

/**
 * Get the current connection state (for synchronous queries from other modules).
 */
export function getConnectionState(): ConnectionState {
  return _connectionState;
}

/**
 * Get the last known companion status.
 */
export function getLastStatus(): LocalStatus {
  return { ..._lastStatus };
}
