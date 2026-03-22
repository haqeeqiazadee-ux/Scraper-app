// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod server;
mod lib;

use std::sync::Arc;

use lib::{
    get_config, get_server_logs, get_server_status, get_version, open_data_dir, restart_server,
    set_config, start_local_server, stop_local_server, AppState,
};

fn main() {
    // Load configuration from disk (or create default)
    let config = config::AppConfig::load().unwrap_or_default();
    let auto_start = config.auto_start_server;
    let api_port = config.api_port;

    let app_state = AppState {
        server: Arc::new(server::ServerManager::default()),
        config: std::sync::Mutex::new(config),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            start_local_server,
            stop_local_server,
            get_server_status,
            restart_server,
            get_config,
            set_config,
            get_server_logs,
            open_data_dir,
            get_version,
        ])
        .setup(move |app| {
            #[cfg(debug_assertions)]
            {
                let window = app
                    .get_webview_window("main")
                    .expect("failed to get main window");
                window.open_devtools();
            }

            // Auto-start server if configured
            if auto_start {
                let state: tauri::State<'_, AppState> = app.state();
                match state.server.start(api_port) {
                    Ok(_) => {
                        server::start_health_check_loop(Arc::clone(&state.server));
                    }
                    Err(e) => {
                        eprintln!("Failed to auto-start server: {}", e);
                    }
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Gracefully stop the server on window close
                let app = window.app_handle();
                if let Some(state) = app.try_state::<AppState>() {
                    let _ = state.server.stop();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
