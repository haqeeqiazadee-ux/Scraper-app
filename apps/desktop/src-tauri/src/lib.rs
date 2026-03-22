//! Tauri command handlers for the AI Scraper Desktop application.
//!
//! Provides commands for server management, configuration, and log viewing.

pub mod config;
pub mod server;

use std::sync::Arc;

use tauri::State;

use crate::config::{AppConfig, AppConfigUpdate};
use crate::server::{ServerManager, ServerStatus};

/// Application state managed by Tauri.
pub struct AppState {
    pub server: Arc<ServerManager>,
    pub config: std::sync::Mutex<AppConfig>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            server: Arc::new(ServerManager::default()),
            config: std::sync::Mutex::new(AppConfig::default()),
        }
    }
}

// ---------------------------------------------------------------------------
// Server commands
// ---------------------------------------------------------------------------

/// Start the local Python uvicorn control-plane server.
#[tauri::command]
pub async fn start_local_server(state: State<'_, AppState>) -> Result<ServerStatus, String> {
    let port = {
        let config = state.config.lock().map_err(|e| e.to_string())?;
        config.api_port
    };

    let status = state.server.start(port)?;

    // Start health check loop
    server::start_health_check_loop(Arc::clone(&state.server));

    Ok(status)
}

/// Stop the local Python control-plane server.
#[tauri::command]
pub async fn stop_local_server(state: State<'_, AppState>) -> Result<ServerStatus, String> {
    state.server.stop()
}

/// Get the current server status.
#[tauri::command]
pub async fn get_server_status(state: State<'_, AppState>) -> Result<ServerStatus, String> {
    state.server.get_status()
}

/// Restart the server (stop then start).
#[tauri::command]
pub async fn restart_server(state: State<'_, AppState>) -> Result<ServerStatus, String> {
    state.server.stop()?;
    state.server.reset_restart_count();

    let port = {
        let config = state.config.lock().map_err(|e| e.to_string())?;
        config.api_port
    };

    let status = state.server.start(port)?;
    server::start_health_check_loop(Arc::clone(&state.server));
    Ok(status)
}

// ---------------------------------------------------------------------------
// Configuration commands
// ---------------------------------------------------------------------------

/// Get the current application configuration.
#[tauri::command]
pub async fn get_config(state: State<'_, AppState>) -> Result<AppConfig, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.clone())
}

/// Update the application configuration with a partial update.
#[tauri::command]
pub async fn set_config(
    state: State<'_, AppState>,
    update: AppConfigUpdate,
) -> Result<AppConfig, String> {
    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.update(update)?;
    Ok(config.clone())
}

// ---------------------------------------------------------------------------
// Log commands
// ---------------------------------------------------------------------------

/// Read the last N lines from the server log file.
#[tauri::command]
pub async fn get_server_logs(
    state: State<'_, AppState>,
    lines: Option<usize>,
) -> Result<Vec<String>, String> {
    let n = lines.unwrap_or(100);
    state.server.tail_logs(n)
}

// ---------------------------------------------------------------------------
// Utility commands
// ---------------------------------------------------------------------------

/// Open the application data directory in the system file explorer.
#[tauri::command]
pub async fn open_data_dir(state: State<'_, AppState>) -> Result<(), String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    config.open_data_dir()
}

/// Return the current application version.
#[tauri::command]
pub async fn get_version() -> Result<String, String> {
    Ok(env!("CARGO_PKG_VERSION").to_string())
}
