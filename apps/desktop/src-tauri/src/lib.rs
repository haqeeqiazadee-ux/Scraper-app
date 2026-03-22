use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::State;

/// Holds the state of the local Python control-plane server process.
pub struct ServerState {
    /// PID of the running uvicorn process, if any.
    pid: Mutex<Option<u32>>,
    /// Whether the server is currently running.
    running: Mutex<bool>,
}

impl Default for ServerState {
    fn default() -> Self {
        Self {
            pid: Mutex::new(None),
            running: Mutex::new(false),
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
    pub port: u16,
    pub mode: String,
}

/// Start the local Python uvicorn control-plane server as a sidecar process.
///
/// The server runs on 127.0.0.1:8321 with SQLite storage, filesystem object
/// storage, and in-memory queue/cache — suitable for desktop single-user mode.
#[tauri::command]
pub async fn start_local_server(state: State<'_, ServerState>) -> Result<ServerStatus, String> {
    let mut running = state.running.lock().map_err(|e| e.to_string())?;
    let mut pid_lock = state.pid.lock().map_err(|e| e.to_string())?;

    if *running {
        return Ok(ServerStatus {
            running: true,
            pid: *pid_lock,
            port: 8321,
            mode: "desktop".to_string(),
        });
    }

    // Spawn the Python uvicorn process
    let child = std::process::Command::new("python")
        .args([
            "-m",
            "uvicorn",
            "services.control_plane.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8321",
        ])
        .env("SCRAPER_MODE", "desktop")
        .env("SCRAPER_DB_URL", "sqlite:///scraper_desktop.db")
        .env("SCRAPER_STORAGE_BACKEND", "filesystem")
        .env("SCRAPER_QUEUE_BACKEND", "memory")
        .env("SCRAPER_CACHE_BACKEND", "memory")
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start local server: {}", e))?;

    let child_pid = child.id();
    *pid_lock = Some(child_pid);
    *running = true;

    Ok(ServerStatus {
        running: true,
        pid: Some(child_pid),
        port: 8321,
        mode: "desktop".to_string(),
    })
}

/// Stop the local Python control-plane server process.
#[tauri::command]
pub async fn stop_local_server(state: State<'_, ServerState>) -> Result<ServerStatus, String> {
    let mut running = state.running.lock().map_err(|e| e.to_string())?;
    let mut pid_lock = state.pid.lock().map_err(|e| e.to_string())?;

    if !*running {
        return Ok(ServerStatus {
            running: false,
            pid: None,
            port: 8321,
            mode: "desktop".to_string(),
        });
    }

    if let Some(pid) = *pid_lock {
        // Kill the process tree
        #[cfg(target_os = "windows")]
        {
            let _ = std::process::Command::new("taskkill")
                .args(["/PID", &pid.to_string(), "/T", "/F"])
                .output();
        }

        #[cfg(not(target_os = "windows"))]
        {
            let _ = std::process::Command::new("kill")
                .args(["-TERM", &pid.to_string()])
                .output();
        }
    }

    *pid_lock = None;
    *running = false;

    Ok(ServerStatus {
        running: false,
        pid: None,
        port: 8321,
        mode: "desktop".to_string(),
    })
}

/// Check whether the local control-plane server is currently running.
#[tauri::command]
pub async fn get_status(state: State<'_, ServerState>) -> Result<ServerStatus, String> {
    let running = state.running.lock().map_err(|e| e.to_string())?;
    let pid_lock = state.pid.lock().map_err(|e| e.to_string())?;

    Ok(ServerStatus {
        running: *running,
        pid: *pid_lock,
        port: 8321,
        mode: "desktop".to_string(),
    })
}

/// Return the current application version from Cargo.toml.
#[tauri::command]
pub async fn get_version() -> Result<String, String> {
    Ok(env!("CARGO_PKG_VERSION").to_string())
}
