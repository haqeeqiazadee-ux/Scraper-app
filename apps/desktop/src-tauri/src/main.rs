// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod lib;

use lib::{get_status, get_version, start_local_server, stop_local_server};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            start_local_server,
            stop_local_server,
            get_status,
            get_version,
        ])
        .setup(|app| {
            // System tray integration placeholder
            // Tray icon is configured via tauri.conf.json trayIcon field
            // Custom tray menu and event handling will be added in EXE-002

            #[cfg(debug_assertions)]
            {
                let window = app
                    .get_webview_window("main")
                    .expect("failed to get main window");
                window.open_devtools();
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            // Handle window close: minimize to tray instead of quitting (placeholder)
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // For now, just close normally.
                // In EXE-002, this will minimize to system tray instead.
                let _ = api;
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
