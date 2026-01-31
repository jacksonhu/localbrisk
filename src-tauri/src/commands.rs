//! Tauri 命令模块 - 所有对外暴露的命令

use crate::settings::{self, AppSettings};

/// 获取应用信息
#[tauri::command]
pub fn get_app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "LocalBrisk",
        "version": "0.1.0",
        "description": "本地化全能 AI 智能体工作站"
    })
}

/// 健康检查命令
#[tauri::command]
pub fn health_check() -> String {
    "OK".to_string()
}

/// 设置是否在退出时保持后端运行
#[tauri::command]
pub fn set_keep_backend_running(keep: bool) -> Result<(), String> {
    settings::set_keep_backend_running(keep)
}

/// 获取是否在退出时保持后端运行
#[tauri::command]
pub fn get_keep_backend_running() -> bool {
    settings::get_keep_backend_running()
}

/// 获取所有应用设置
#[tauri::command]
pub fn get_app_settings() -> AppSettings {
    let settings = settings::load();
    crate::logger::log(&format!("获取应用设置: {:?}", settings));
    settings
}

/// 保存所有应用设置
#[tauri::command]
pub fn save_app_settings(settings: AppSettings) -> Result<(), String> {
    use std::sync::atomic::Ordering;

    settings::KEEP_BACKEND_RUNNING.store(settings.keep_backend_running, Ordering::SeqCst);
    crate::logger::log(&format!("保存应用设置: {:?}", settings));
    settings::save(&settings)
}
