/**
 * Native Messaging Client — connects extension to local companion host.
 *
 * Uses Chrome Native Messaging (chrome.runtime.connectNative) to communicate
 * with the companion app via length-prefixed JSON over stdin/stdout.
 *
 * Message protocol:
 *   { type: string, payload: unknown, id: string }
 *
 * The companion host name is "com.scraper.companion" (must match the
 * native messaging host manifest installed by apps/companion/install.py).
 */

const HOST_NAME = "com.scraper.companion";

/** Maximum number of reconnection attempts before giving up. */
const MAX_RECONNECT_ATTEMPTS = 5;

/** Base delay (ms) between reconnection attempts — doubled each time. */
const RECONNECT_BASE_DELAY_MS = 1000;

/** Timeout (ms) for waiting for a response to a specific message ID. */
const RESPONSE_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface NativeMessage {
  type: string;
  payload: unknown;
  id: string;
}

export interface NativeResponse {
  type: string;
  payload: unknown;
  id: string;
  success: boolean;
  error?: string;
}

export type MessageHandler = (message: NativeResponse) => void;

// ---------------------------------------------------------------------------
// ID generation
// ---------------------------------------------------------------------------

let _counter = 0;

function generateId(): string {
  _counter += 1;
  return `msg_${Date.now()}_${_counter}`;
}

// ---------------------------------------------------------------------------
// NativeMessagingClient
// ---------------------------------------------------------------------------

export class NativeMessagingClient {
  private _port: chrome.runtime.Port | null = null;
  private _connected = false;
  private _reconnectAttempts = 0;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _handlers: Set<MessageHandler> = new Set();
  private _pendingResponses: Map<
    string,
    { resolve: (value: NativeResponse) => void; reject: (err: Error) => void; timer: ReturnType<typeof setTimeout> }
  > = new Map();
  private _autoReconnect = true;

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  /**
   * Open a native messaging port to the companion host.
   * Resolves when the port is open; rejects if the host is unreachable.
   */
  connect(): void {
    if (this._connected && this._port) {
      return;
    }

    this._autoReconnect = true;

    try {
      this._port = chrome.runtime.connectNative(HOST_NAME);

      this._port.onMessage.addListener((msg: NativeResponse) => {
        this._onPortMessage(msg);
      });

      this._port.onDisconnect.addListener(() => {
        this._onPortDisconnect();
      });

      this._connected = true;
      this._reconnectAttempts = 0;

      console.log("[NativeMessaging] Connected to companion host");
    } catch (err) {
      this._connected = false;
      console.error("[NativeMessaging] Failed to connect:", err);
      this._scheduleReconnect();
    }
  }

  /**
   * Gracefully close the native messaging port.
   */
  disconnect(): void {
    this._autoReconnect = false;
    this._clearReconnectTimer();
    this._cleanup();
  }

  /**
   * Send a message to the companion host and wait for a correlated response.
   *
   * @param type    Message type (e.g. "execute_task", "health_check").
   * @param payload Arbitrary payload for the companion.
   * @returns       The companion's response, correlated by message ID.
   */
  sendMessage(type: string, payload: unknown = {}): Promise<NativeResponse> {
    return new Promise((resolve, reject) => {
      if (!this._connected || !this._port) {
        reject(new Error("Not connected to companion host"));
        return;
      }

      const id = generateId();
      const message: NativeMessage = { type, payload, id };

      // Set up timeout for response
      const timer = setTimeout(() => {
        this._pendingResponses.delete(id);
        reject(new Error(`Response timeout for message ${id} (type: ${type})`));
      }, RESPONSE_TIMEOUT_MS);

      this._pendingResponses.set(id, { resolve, reject, timer });

      try {
        this._port.postMessage(message);
      } catch (err) {
        clearTimeout(timer);
        this._pendingResponses.delete(id);
        reject(err instanceof Error ? err : new Error(String(err)));
      }
    });
  }

  /**
   * Register a handler for all incoming messages (including unsolicited ones).
   */
  onMessage(handler: MessageHandler): () => void {
    this._handlers.add(handler);
    return () => {
      this._handlers.delete(handler);
    };
  }

  /**
   * Whether the native messaging port is currently connected.
   */
  isConnected(): boolean {
    return this._connected;
  }

  // -----------------------------------------------------------------------
  // Internal
  // -----------------------------------------------------------------------

  private _onPortMessage(msg: NativeResponse): void {
    // Check if this is a response to a pending request
    if (msg.id && this._pendingResponses.has(msg.id)) {
      const pending = this._pendingResponses.get(msg.id)!;
      clearTimeout(pending.timer);
      this._pendingResponses.delete(msg.id);
      pending.resolve(msg);
    }

    // Notify all general handlers regardless
    for (const handler of this._handlers) {
      try {
        handler(msg);
      } catch (err) {
        console.error("[NativeMessaging] Handler error:", err);
      }
    }
  }

  private _onPortDisconnect(): void {
    const lastError = chrome.runtime.lastError;
    console.warn(
      "[NativeMessaging] Port disconnected:",
      lastError?.message ?? "unknown reason"
    );

    this._cleanup();

    if (this._autoReconnect) {
      this._scheduleReconnect();
    }
  }

  private _cleanup(): void {
    this._connected = false;

    if (this._port) {
      try {
        this._port.disconnect();
      } catch {
        // Port may already be disconnected
      }
      this._port = null;
    }

    // Reject all pending responses
    for (const [id, pending] of this._pendingResponses) {
      clearTimeout(pending.timer);
      pending.reject(new Error("Connection closed"));
      this._pendingResponses.delete(id);
    }
  }

  private _scheduleReconnect(): void {
    if (this._reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error(
        "[NativeMessaging] Max reconnection attempts reached — giving up"
      );
      return;
    }

    this._clearReconnectTimer();

    const delay =
      RECONNECT_BASE_DELAY_MS * Math.pow(2, this._reconnectAttempts);
    this._reconnectAttempts += 1;

    console.log(
      `[NativeMessaging] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`
    );

    this._reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private _clearReconnectTimer(): void {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }
}

// ---------------------------------------------------------------------------
// Singleton
// ---------------------------------------------------------------------------

export const nativeMessaging = new NativeMessagingClient();
