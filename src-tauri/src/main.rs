//! LocalBrisk - Tauri 主程序入口
//! 负责窗口管理、系统原生集成

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod commands;
mod file_ops;
mod logger;
mod menu;
mod settings;

use logger::log;
use std::sync::atomic::Ordering;
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .menu(|app| menu::create(app))
        .on_menu_event(|app, event| menu::handle_event(app, event.id().as_ref()))
        .invoke_handler(tauri::generate_handler![
            // 应用信息
            commands::get_app_info,
            commands::health_check,
            // 后端服务
            backend::check_backend_health,
            // 文件操作
            file_ops::list_directory,
            file_ops::create_directory,
            file_ops::delete_path,
            file_ops::path_exists,
            file_ops::get_file_info,
            file_ops::read_text_file,
            file_ops::write_text_file,
            file_ops::read_binary_file,
            // 设置
            commands::set_keep_backend_running,
            commands::get_keep_backend_running,
            commands::get_app_settings,
            commands::save_app_settings,
        ])
        .setup(|app| {
            log("========== LocalBrisk 启动 ==========");
            log(&format!("Tauri version: {}", tauri::VERSION));

            // 初始化设置
            settings::init_global_state();

            // 启动后端服务（仅 Release 模式）
            #[cfg(not(debug_assertions))]
            backend::start(app.handle().clone());

            #[cfg(debug_assertions)]
            log("开发模式: 跳过 sidecar 启动，由 dev.sh 管理后端");

            // 初始化主窗口
            setup_main_window(app);

            log("LocalBrisk 启动完成！");
            println!("LocalBrisk 启动成功！");
            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let keep_running = settings::KEEP_BACKEND_RUNNING.load(Ordering::SeqCst);
                log(&format!(
                    "窗口关闭请求, keepBackendRunning = {}",
                    keep_running
                ));

                #[cfg(not(debug_assertions))]
                backend::stop();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn setup_main_window(app: &tauri::App) {
    match app.get_webview_window("main") {
        Some(window) => {
            log(&format!("主窗口已创建: {:?}", window.label()));

            if let Ok(url) = window.url() {
                log(&format!("窗口 URL: {}", url));
            }

            #[cfg(debug_assertions)]
            {
                window.open_devtools();
                log("开发模式: 已打开开发者工具");
            }
        }
        None => {
            log("错误: 主窗口未创建！");
        }
    }
}
