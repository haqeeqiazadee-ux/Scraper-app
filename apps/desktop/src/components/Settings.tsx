import { useEffect, useState } from "react";
import { useTauri } from "../hooks/useTauri";

type AppConfig = {
  api_port: number;
  data_dir: string;
  log_level: string;
  ai_provider: string;
  ai_api_key: string;
  ai_base_url: string;
  proxy_url: string;
  proxy_enabled: boolean;
  auto_start_server: boolean;
  max_concurrent_tasks: number;
  theme: string;
};

type AppConfigUpdate = Partial<AppConfig>;

const LOG_LEVELS = ["debug", "info", "warning", "error"];
const AI_PROVIDERS = ["none", "gemini", "openai", "anthropic", "ollama"];

/**
 * Settings panel for configuring the desktop application.
 * Persists settings via Tauri invoke to ~/.scraper-app/config.json.
 */
export function Settings() {
  const { invoke } = useTauri();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Local form state
  const [formState, setFormState] = useState<AppConfigUpdate>({});

  const loadConfig = async () => {
    try {
      const cfg = await invoke<AppConfig>("get_config");
      setConfig(cfg);
      setFormState({});
      setError(null);
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await invoke<AppConfig>("set_config", { update: formState });
      setConfig(updated);
      setFormState({});
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleOpenDataDir = async () => {
    try {
      await invoke("open_data_dir");
    } catch (err) {
      setError(String(err));
    }
  };

  const getValue = <K extends keyof AppConfig>(key: K): AppConfig[K] => {
    if (key in formState && formState[key] !== undefined) {
      return formState[key] as AppConfig[K];
    }
    return config ? config[key] : ("" as unknown as AppConfig[K]);
  };

  const updateField = <K extends keyof AppConfig>(key: K, value: AppConfig[K]) => {
    setFormState((prev) => ({ ...prev, [key]: value }));
  };

  const hasChanges = Object.keys(formState).length > 0;

  if (!config) {
    return (
      <div style={styles.container}>
        <p style={{ color: "#999" }}>Loading configuration...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Settings</h2>

      {/* Server Settings */}
      <fieldset style={styles.fieldset}>
        <legend style={styles.legend}>Server</legend>

        <label style={styles.label}>
          <span>API Port</span>
          <input
            type="number"
            min={1024}
            max={65535}
            value={getValue("api_port")}
            onChange={(e) => updateField("api_port", Number(e.target.value))}
            style={styles.input}
          />
        </label>

        <label style={styles.label}>
          <span>Data Directory</span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <input
              type="text"
              value={getValue("data_dir")}
              onChange={(e) => updateField("data_dir", e.target.value)}
              style={{ ...styles.input, flex: 1 }}
            />
            <button onClick={handleOpenDataDir} style={styles.smallButton}>
              Open
            </button>
          </div>
        </label>

        <label style={styles.label}>
          <span>Log Level</span>
          <select
            value={getValue("log_level")}
            onChange={(e) => updateField("log_level", e.target.value)}
            style={styles.input}
          >
            {LOG_LEVELS.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>

        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={getValue("auto_start_server")}
            onChange={(e) => updateField("auto_start_server", e.target.checked)}
          />
          <span>Auto-start server on app launch</span>
        </label>

        <label style={styles.label}>
          <span>Max Concurrent Tasks</span>
          <input
            type="number"
            min={1}
            max={50}
            value={getValue("max_concurrent_tasks")}
            onChange={(e) => updateField("max_concurrent_tasks", Number(e.target.value))}
            style={styles.input}
          />
        </label>
      </fieldset>

      {/* AI Provider Settings */}
      <fieldset style={styles.fieldset}>
        <legend style={styles.legend}>AI Provider</legend>

        <label style={styles.label}>
          <span>Provider</span>
          <select
            value={getValue("ai_provider")}
            onChange={(e) => updateField("ai_provider", e.target.value)}
            style={styles.input}
          >
            {AI_PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {p === "none" ? "None (deterministic only)" : p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </label>

        {getValue("ai_provider") !== "none" && (
          <>
            <label style={styles.label}>
              <span>API Key</span>
              <input
                type="password"
                value={getValue("ai_api_key")}
                onChange={(e) => updateField("ai_api_key", e.target.value)}
                placeholder="Enter API key..."
                style={styles.input}
              />
            </label>

            {getValue("ai_provider") === "ollama" && (
              <label style={styles.label}>
                <span>Base URL</span>
                <input
                  type="text"
                  value={getValue("ai_base_url")}
                  onChange={(e) => updateField("ai_base_url", e.target.value)}
                  placeholder="http://localhost:11434"
                  style={styles.input}
                />
              </label>
            )}
          </>
        )}
      </fieldset>

      {/* Proxy Settings */}
      <fieldset style={styles.fieldset}>
        <legend style={styles.legend}>Proxy</legend>

        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={getValue("proxy_enabled")}
            onChange={(e) => updateField("proxy_enabled", e.target.checked)}
          />
          <span>Enable proxy for all requests</span>
        </label>

        {getValue("proxy_enabled") && (
          <label style={styles.label}>
            <span>Proxy URL</span>
            <input
              type="text"
              value={getValue("proxy_url")}
              onChange={(e) => updateField("proxy_url", e.target.value)}
              placeholder="socks5://127.0.0.1:1080"
              style={styles.input}
            />
          </label>
        )}
      </fieldset>

      {/* Actions */}
      <div style={styles.actions}>
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          style={{
            ...styles.primaryButton,
            opacity: !hasChanges || saving ? 0.5 : 1,
            cursor: !hasChanges || saving ? "not-allowed" : "pointer",
          }}
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>

        {hasChanges && (
          <button onClick={() => setFormState({})} style={styles.secondaryButton}>
            Discard Changes
          </button>
        )}
      </div>

      {saved && (
        <div style={styles.successBanner}>Settings saved successfully.</div>
      )}

      {error && (
        <div style={styles.errorBanner}>{error}</div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "1.5rem",
    maxWidth: "600px",
  },
  heading: {
    fontSize: "1.25rem",
    fontWeight: 600,
    marginBottom: "1.5rem",
  },
  fieldset: {
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "1rem 1.25rem",
    marginBottom: "1.25rem",
  },
  legend: {
    fontSize: "0.875rem",
    fontWeight: 600,
    color: "#374151",
    padding: "0 0.5rem",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    marginBottom: "0.75rem",
    fontSize: "0.875rem",
    color: "#4b5563",
  },
  checkboxLabel: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    marginBottom: "0.75rem",
    fontSize: "0.875rem",
    color: "#4b5563",
  },
  input: {
    padding: "0.5rem 0.75rem",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    fontSize: "0.875rem",
    outline: "none",
  },
  smallButton: {
    padding: "0.5rem 0.75rem",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    background: "#f9fafb",
    fontSize: "0.8rem",
    cursor: "pointer",
  },
  actions: {
    display: "flex",
    gap: "0.75rem",
    marginTop: "1.5rem",
  },
  primaryButton: {
    padding: "0.6rem 1.25rem",
    borderRadius: "6px",
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontWeight: 500,
    fontSize: "0.875rem",
  },
  secondaryButton: {
    padding: "0.6rem 1.25rem",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    background: "#fff",
    color: "#374151",
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  successBanner: {
    marginTop: "1rem",
    padding: "0.75rem",
    background: "#f0fdf4",
    border: "1px solid #bbf7d0",
    borderRadius: "6px",
    color: "#166534",
    fontSize: "0.875rem",
  },
  errorBanner: {
    marginTop: "1rem",
    padding: "0.75rem",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "6px",
    color: "#dc2626",
    fontSize: "0.875rem",
  },
};

export default Settings;
