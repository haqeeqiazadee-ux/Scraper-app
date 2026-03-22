//! Desktop configuration management.
//!
//! Reads and writes configuration from ~/.scraper-app/config.json.
//! Provides typed access to all desktop-specific settings.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

/// Default config file name.
const CONFIG_FILE_NAME: &str = "config.json";

/// Desktop application configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Port for the local control plane API server.
    #[serde(default = "default_api_port")]
    pub api_port: u16,

    /// Directory for storing application data (database, artifacts).
    #[serde(default = "default_data_dir")]
    pub data_dir: String,

    /// Log level: debug, info, warning, error.
    #[serde(default = "default_log_level")]
    pub log_level: String,

    /// AI provider: gemini, openai, anthropic, ollama, none.
    #[serde(default = "default_ai_provider")]
    pub ai_provider: String,

    /// API key for the configured AI provider.
    #[serde(default)]
    pub ai_api_key: String,

    /// AI provider base URL (for Ollama or custom endpoints).
    #[serde(default)]
    pub ai_base_url: String,

    /// Proxy configuration URL (e.g., socks5://127.0.0.1:1080).
    #[serde(default)]
    pub proxy_url: String,

    /// Whether to use proxy for all requests.
    #[serde(default)]
    pub proxy_enabled: bool,

    /// Whether to auto-start the server on app launch.
    #[serde(default = "default_auto_start")]
    pub auto_start_server: bool,

    /// Maximum concurrent tasks.
    #[serde(default = "default_max_concurrent")]
    pub max_concurrent_tasks: u32,

    /// Theme preference: light, dark, system.
    #[serde(default = "default_theme")]
    pub theme: String,
}

fn default_api_port() -> u16 {
    8321
}

fn default_data_dir() -> String {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
    home.join(".scraper-app").display().to_string()
}

fn default_log_level() -> String {
    "info".to_string()
}

fn default_ai_provider() -> String {
    "none".to_string()
}

fn default_auto_start() -> bool {
    true
}

fn default_max_concurrent() -> u32 {
    5
}

fn default_theme() -> String {
    "system".to_string()
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            api_port: default_api_port(),
            data_dir: default_data_dir(),
            log_level: default_log_level(),
            ai_provider: default_ai_provider(),
            ai_api_key: String::new(),
            ai_base_url: String::new(),
            proxy_url: String::new(),
            proxy_enabled: false,
            auto_start_server: default_auto_start(),
            max_concurrent_tasks: default_max_concurrent(),
            theme: default_theme(),
        }
    }
}

impl AppConfig {
    /// Get the path to the config file.
    fn config_path() -> PathBuf {
        let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
        home.join(".scraper-app").join(CONFIG_FILE_NAME)
    }

    /// Load configuration from disk. Returns default config if file doesn't exist.
    pub fn load() -> Result<Self, String> {
        let path = Self::config_path();

        if !path.exists() {
            let config = Self::default();
            // Write default config to disk so user can see the file
            config.save()?;
            return Ok(config);
        }

        let contents = std::fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read config file {}: {}", path.display(), e))?;

        serde_json::from_str(&contents)
            .map_err(|e| format!("Failed to parse config file: {}", e))
    }

    /// Save configuration to disk.
    pub fn save(&self) -> Result<(), String> {
        let path = Self::config_path();

        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create config directory: {}", e))?;
        }

        let contents = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Failed to serialize config: {}", e))?;

        std::fs::write(&path, contents)
            .map_err(|e| format!("Failed to write config file: {}", e))?;

        Ok(())
    }

    /// Update specific fields from a partial config. Only non-empty/non-default
    /// fields in the update are applied.
    pub fn update(&mut self, update: AppConfigUpdate) -> Result<(), String> {
        if let Some(port) = update.api_port {
            self.api_port = port;
        }
        if let Some(dir) = update.data_dir {
            self.data_dir = dir;
        }
        if let Some(level) = update.log_level {
            self.log_level = level;
        }
        if let Some(provider) = update.ai_provider {
            self.ai_provider = provider;
        }
        if let Some(key) = update.ai_api_key {
            self.ai_api_key = key;
        }
        if let Some(url) = update.ai_base_url {
            self.ai_base_url = url;
        }
        if let Some(url) = update.proxy_url {
            self.proxy_url = url;
        }
        if let Some(enabled) = update.proxy_enabled {
            self.proxy_enabled = enabled;
        }
        if let Some(auto_start) = update.auto_start_server {
            self.auto_start_server = auto_start;
        }
        if let Some(max) = update.max_concurrent_tasks {
            self.max_concurrent_tasks = max;
        }
        if let Some(theme) = update.theme {
            self.theme = theme;
        }

        self.save()
    }

    /// Open the data directory in the system file explorer.
    pub fn open_data_dir(&self) -> Result<(), String> {
        let path = PathBuf::from(&self.data_dir);
        if !path.exists() {
            std::fs::create_dir_all(&path)
                .map_err(|e| format!("Failed to create data directory: {}", e))?;
        }

        #[cfg(target_os = "windows")]
        {
            Command::new("explorer")
                .arg(&self.data_dir)
                .spawn()
                .map_err(|e| format!("Failed to open directory: {}", e))?;
        }

        #[cfg(target_os = "macos")]
        {
            std::process::Command::new("open")
                .arg(&self.data_dir)
                .spawn()
                .map_err(|e| format!("Failed to open directory: {}", e))?;
        }

        #[cfg(target_os = "linux")]
        {
            std::process::Command::new("xdg-open")
                .arg(&self.data_dir)
                .spawn()
                .map_err(|e| format!("Failed to open directory: {}", e))?;
        }

        Ok(())
    }
}

/// Partial configuration update. All fields are optional; only provided
/// fields will be applied to the existing configuration.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppConfigUpdate {
    pub api_port: Option<u16>,
    pub data_dir: Option<String>,
    pub log_level: Option<String>,
    pub ai_provider: Option<String>,
    pub ai_api_key: Option<String>,
    pub ai_base_url: Option<String>,
    pub proxy_url: Option<String>,
    pub proxy_enabled: Option<bool>,
    pub auto_start_server: Option<bool>,
    pub max_concurrent_tasks: Option<u32>,
    pub theme: Option<String>,
}
