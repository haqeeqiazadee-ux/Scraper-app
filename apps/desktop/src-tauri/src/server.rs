//! Server management module for the embedded Python control-plane process.
//!
//! Manages the full lifecycle: spawn uvicorn with desktop-appropriate env vars,
//! health check polling, graceful shutdown with timeout, and automatic restart
//! on crash.

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

/// Environment variables set for the embedded desktop control plane.
const ENV_STORAGE_BACKEND: &str = "sqlite";
const ENV_QUEUE_BACKEND: &str = "memory";
const ENV_CACHE_BACKEND: &str = "memory";

/// Default port for the local control plane.
const DEFAULT_PORT: u16 = 8321;

/// Health check interval in seconds.
const HEALTH_CHECK_INTERVAL_SECS: u64 = 5;

/// Graceful shutdown timeout in seconds before force-killing.
const SHUTDOWN_TIMEOUT_SECS: u64 = 10;

/// Maximum number of automatic restart attempts before giving up.
const MAX_RESTART_ATTEMPTS: u32 = 5;

/// Cooldown between restart attempts in seconds.
const RESTART_COOLDOWN_SECS: u64 = 3;

/// Status of the embedded server process.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
    pub port: u16,
    pub mode: String,
    pub uptime_secs: Option<u64>,
    pub restart_count: u32,
    pub health_ok: bool,
}

/// Internal state for the server manager.
pub struct ServerManager {
    child: Mutex<Option<Child>>,
    running: Mutex<bool>,
    port: Mutex<u16>,
    start_time: Mutex<Option<Instant>>,
    restart_count: Mutex<u32>,
    health_ok: Mutex<bool>,
    log_file_path: Mutex<Option<PathBuf>>,
    /// Flag to signal the health check loop to stop.
    shutdown_signal: Arc<Mutex<bool>>,
}

impl Default for ServerManager {
    fn default() -> Self {
        Self {
            child: Mutex::new(None),
            running: Mutex::new(false),
            port: Mutex::new(DEFAULT_PORT),
            start_time: Mutex::new(None),
            restart_count: Mutex::new(0),
            health_ok: Mutex::new(false),
            log_file_path: Mutex::new(None),
            shutdown_signal: Arc::new(Mutex::new(false)),
        }
    }
}

impl ServerManager {
    /// Get the data directory (~/.scraper-app/).
    fn data_dir() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".scraper-app")
    }

    /// Get the logs directory (~/.scraper-app/logs/).
    fn logs_dir() -> PathBuf {
        Self::data_dir().join("logs")
    }

    /// Get the SQLite database URL.
    fn database_url() -> String {
        let db_path = Self::data_dir().join("data.db");
        format!("sqlite:///{}", db_path.display())
    }

    /// Ensure required directories exist.
    fn ensure_dirs() -> Result<(), String> {
        let data_dir = Self::data_dir();
        std::fs::create_dir_all(&data_dir)
            .map_err(|e| format!("Failed to create data dir {}: {}", data_dir.display(), e))?;
        let logs_dir = Self::logs_dir();
        std::fs::create_dir_all(&logs_dir)
            .map_err(|e| format!("Failed to create logs dir {}: {}", logs_dir.display(), e))?;
        Ok(())
    }

    /// Start the embedded control-plane server.
    pub fn start(&self, port: u16) -> Result<ServerStatus, String> {
        let mut running = self.running.lock().map_err(|e| e.to_string())?;
        if *running {
            return self.get_status_inner();
        }

        Self::ensure_dirs()?;

        let log_file_path = Self::logs_dir().join("server.log");
        let log_file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_file_path)
            .map_err(|e| format!("Failed to open log file: {}", e))?;

        let log_file_stderr = log_file
            .try_clone()
            .map_err(|e| format!("Failed to clone log file handle: {}", e))?;

        let child = Command::new("python")
            .args([
                "-m",
                "uvicorn",
                "services.control_plane.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                &port.to_string(),
            ])
            .env("SCRAPER_MODE", "desktop")
            .env("STORAGE_BACKEND", ENV_STORAGE_BACKEND)
            .env("QUEUE_BACKEND", ENV_QUEUE_BACKEND)
            .env("CACHE_BACKEND", ENV_CACHE_BACKEND)
            .env("DATABASE_URL", Self::database_url())
            .env("SCRAPER_STORAGE_BACKEND", ENV_STORAGE_BACKEND)
            .env("SCRAPER_QUEUE_BACKEND", ENV_QUEUE_BACKEND)
            .env("SCRAPER_CACHE_BACKEND", ENV_CACHE_BACKEND)
            .env("SCRAPER_DB_URL", Self::database_url())
            .env("LOG_LEVEL", "info")
            .stdout(Stdio::from(log_file))
            .stderr(Stdio::from(log_file_stderr))
            .spawn()
            .map_err(|e| format!("Failed to start local server: {}", e))?;

        let pid = child.id();

        let mut child_lock = self.child.lock().map_err(|e| e.to_string())?;
        *child_lock = Some(child);

        let mut port_lock = self.port.lock().map_err(|e| e.to_string())?;
        *port_lock = port;

        let mut start_time = self.start_time.lock().map_err(|e| e.to_string())?;
        *start_time = Some(Instant::now());

        let mut log_path = self.log_file_path.lock().map_err(|e| e.to_string())?;
        *log_path = Some(log_file_path);

        *running = true;

        // Reset shutdown signal
        if let Ok(mut sig) = self.shutdown_signal.lock() {
            *sig = false;
        }

        Ok(ServerStatus {
            running: true,
            pid: Some(pid),
            port,
            mode: "desktop".to_string(),
            uptime_secs: Some(0),
            restart_count: *self.restart_count.lock().map_err(|e| e.to_string())?,
            health_ok: false, // Will become true after first health check
        })
    }

    /// Stop the embedded control-plane server with graceful shutdown.
    pub fn stop(&self) -> Result<ServerStatus, String> {
        let mut running = self.running.lock().map_err(|e| e.to_string())?;
        if !*running {
            return Ok(ServerStatus {
                running: false,
                pid: None,
                port: *self.port.lock().map_err(|e| e.to_string())?,
                mode: "desktop".to_string(),
                uptime_secs: None,
                restart_count: *self.restart_count.lock().map_err(|e| e.to_string())?,
                health_ok: false,
            });
        }

        // Signal health check loop to stop
        if let Ok(mut sig) = self.shutdown_signal.lock() {
            *sig = true;
        }

        let mut child_lock = self.child.lock().map_err(|e| e.to_string())?;
        if let Some(ref mut child) = *child_lock {
            let pid = child.id();

            // Attempt graceful shutdown first
            #[cfg(target_os = "windows")]
            {
                // On Windows, send Ctrl+C event first, then taskkill if needed
                let _ = Command::new("taskkill")
                    .args(["/PID", &pid.to_string()])
                    .output();
            }

            #[cfg(not(target_os = "windows"))]
            {
                // On Unix, send SIGTERM for graceful shutdown
                let _ = Command::new("kill")
                    .args(["-TERM", &pid.to_string()])
                    .output();
            }

            // Wait for graceful shutdown with timeout
            let deadline = Instant::now() + Duration::from_secs(SHUTDOWN_TIMEOUT_SECS);
            loop {
                match child.try_wait() {
                    Ok(Some(_)) => break, // Process exited
                    Ok(None) => {
                        if Instant::now() >= deadline {
                            // Force kill after timeout
                            #[cfg(target_os = "windows")]
                            {
                                let _ = Command::new("taskkill")
                                    .args(["/PID", &pid.to_string(), "/T", "/F"])
                                    .output();
                            }

                            #[cfg(not(target_os = "windows"))]
                            {
                                let _ = Command::new("kill")
                                    .args(["-9", &pid.to_string()])
                                    .output();
                            }

                            let _ = child.wait(); // Reap the process
                            break;
                        }
                        std::thread::sleep(Duration::from_millis(200));
                    }
                    Err(_) => break,
                }
            }
        }

        *child_lock = None;
        *running = false;

        let mut start_time = self.start_time.lock().map_err(|e| e.to_string())?;
        *start_time = None;

        let mut health = self.health_ok.lock().map_err(|e| e.to_string())?;
        *health = false;

        let port = *self.port.lock().map_err(|e| e.to_string())?;
        let restart_count = *self.restart_count.lock().map_err(|e| e.to_string())?;

        Ok(ServerStatus {
            running: false,
            pid: None,
            port,
            mode: "desktop".to_string(),
            uptime_secs: None,
            restart_count,
            health_ok: false,
        })
    }

    /// Get current server status.
    pub fn get_status(&self) -> Result<ServerStatus, String> {
        self.get_status_inner()
    }

    fn get_status_inner(&self) -> Result<ServerStatus, String> {
        let running = *self.running.lock().map_err(|e| e.to_string())?;
        let port = *self.port.lock().map_err(|e| e.to_string())?;
        let restart_count = *self.restart_count.lock().map_err(|e| e.to_string())?;
        let health_ok = *self.health_ok.lock().map_err(|e| e.to_string())?;

        let pid = if let Ok(child_lock) = self.child.lock() {
            child_lock.as_ref().map(|c| c.id())
        } else {
            None
        };

        let uptime_secs = if let Ok(start_time) = self.start_time.lock() {
            start_time.map(|t| t.elapsed().as_secs())
        } else {
            None
        };

        Ok(ServerStatus {
            running,
            pid,
            port,
            mode: "desktop".to_string(),
            uptime_secs,
            restart_count,
            health_ok,
        })
    }

    /// Check if the server process is still alive. If it crashed, attempt restart.
    pub fn check_and_restart(&self) -> Result<bool, String> {
        let running = *self.running.lock().map_err(|e| e.to_string())?;
        if !running {
            return Ok(false);
        }

        // Check if process is still alive
        let mut child_lock = self.child.lock().map_err(|e| e.to_string())?;
        let process_alive = if let Some(ref mut child) = *child_lock {
            match child.try_wait() {
                Ok(Some(_exit_status)) => false, // Process has exited
                Ok(None) => true,                // Still running
                Err(_) => false,                 // Error checking — assume dead
            }
        } else {
            false
        };

        if process_alive {
            return Ok(true);
        }

        // Process crashed — attempt restart
        drop(child_lock); // Release lock before restarting

        let mut restart_count = self.restart_count.lock().map_err(|e| e.to_string())?;
        if *restart_count >= MAX_RESTART_ATTEMPTS {
            // Too many restarts — give up
            let mut running = self.running.lock().map_err(|e| e.to_string())?;
            *running = false;
            let mut health = self.health_ok.lock().map_err(|e| e.to_string())?;
            *health = false;
            return Err(format!(
                "Server crashed {} times, giving up on restarts",
                MAX_RESTART_ATTEMPTS
            ));
        }

        *restart_count += 1;
        drop(restart_count);

        // Brief cooldown before restart
        std::thread::sleep(Duration::from_secs(RESTART_COOLDOWN_SECS));

        // Mark as not running so start() will proceed
        {
            let mut running = self.running.lock().map_err(|e| e.to_string())?;
            *running = false;
            let mut child_lock = self.child.lock().map_err(|e| e.to_string())?;
            *child_lock = None;
        }

        let port = *self.port.lock().map_err(|e| e.to_string())?;
        self.start(port)?;

        Ok(true)
    }

    /// Perform a health check against the running server.
    pub fn health_check(&self) -> bool {
        let port = match self.port.lock() {
            Ok(p) => *p,
            Err(_) => return false,
        };

        let url = format!("http://127.0.0.1:{}/health", port);

        // Use a simple blocking HTTP request for health check
        let result = std::process::Command::new("curl")
            .args(["-sf", "--max-time", "3", &url])
            .output();

        let healthy = match result {
            Ok(output) => output.status.success(),
            Err(_) => false,
        };

        if let Ok(mut health) = self.health_ok.lock() {
            *health = healthy;
        }

        healthy
    }

    /// Read the last N lines from the server log file.
    pub fn tail_logs(&self, lines: usize) -> Result<Vec<String>, String> {
        let log_path = self
            .log_file_path
            .lock()
            .map_err(|e| e.to_string())?;

        let path = match log_path.as_ref() {
            Some(p) => p.clone(),
            None => {
                // Default log path even if server hasn't started yet
                Self::logs_dir().join("server.log")
            }
        };

        if !path.exists() {
            return Ok(vec![]);
        }

        let file = std::fs::File::open(&path)
            .map_err(|e| format!("Failed to open log file: {}", e))?;

        let reader = BufReader::new(file);
        let all_lines: Vec<String> = reader
            .lines()
            .filter_map(|l| l.ok())
            .collect();

        let start = if all_lines.len() > lines {
            all_lines.len() - lines
        } else {
            0
        };

        Ok(all_lines[start..].to_vec())
    }

    /// Reset the restart counter (e.g., after successful manual restart).
    pub fn reset_restart_count(&self) {
        if let Ok(mut count) = self.restart_count.lock() {
            *count = 0;
        }
    }
}

/// Start a background health check loop. Should be spawned in a separate thread.
pub fn start_health_check_loop(manager: Arc<ServerManager>) {
    let shutdown_signal = Arc::clone(&manager.shutdown_signal);

    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(HEALTH_CHECK_INTERVAL_SECS));

            // Check shutdown signal
            if let Ok(sig) = shutdown_signal.lock() {
                if *sig {
                    break;
                }
            }

            // Check if server is supposed to be running
            let running = match manager.running.lock() {
                Ok(r) => *r,
                Err(_) => break,
            };

            if !running {
                continue;
            }

            // Perform health check
            let healthy = manager.health_check();

            if !healthy {
                // Server might have crashed — check and restart if needed
                match manager.check_and_restart() {
                    Ok(true) => {} // Still running or restarted
                    Ok(false) => break, // Not running anymore
                    Err(_e) => {
                        // Max restarts exceeded — stop the loop
                        break;
                    }
                }
            }
        }
    });
}
