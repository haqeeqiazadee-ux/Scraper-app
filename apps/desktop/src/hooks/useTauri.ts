import { invoke as tauriInvoke } from "@tauri-apps/api/core";

/**
 * Hook for invoking Tauri v2 commands from React components.
 *
 * Provides a typed `invoke` wrapper and detection of whether the app
 * is running inside the Tauri webview or a regular browser (for dev).
 *
 * Usage:
 *   const { invoke, isTauri } = useTauri();
 *   const status = await invoke<ServerStatus>("get_status");
 */

/** Check if running inside Tauri webview. */
function checkIsTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Typed wrapper around Tauri's invoke function.
 * Falls back to a rejected promise when not running in Tauri context.
 */
async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!checkIsTauri()) {
    return Promise.reject(
      new Error(`Not running in Tauri context. Command "${cmd}" is only available in the desktop app.`),
    );
  }
  return tauriInvoke<T>(cmd, args);
}

/**
 * React hook providing Tauri v2 integration utilities.
 */
export function useTauri() {
  const isTauri = checkIsTauri();

  return {
    /** Whether the app is running inside the Tauri webview. */
    isTauri,
    /** Invoke a Tauri command. Type-safe wrapper around @tauri-apps/api/core invoke. */
    invoke,
  };
}
