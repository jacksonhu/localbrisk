//! 应用设置模块 - 统一管理配置项

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};

use crate::logger::log;

/// 全局设置：是否在退出时保持后端运行
pub static KEEP_BACKEND_RUNNING: AtomicBool = AtomicBool::new(true);

/// 应用设置结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    #[serde(default = "default_keep_backend_running")]
    pub keep_backend_running: bool,

    #[serde(default = "default_language")]
    pub language: String,

    #[serde(default)]
    pub enable_local_model: bool,

    #[serde(default)]
    pub local_model: String,

    #[serde(default = "default_local_model_endpoint")]
    pub local_model_endpoint: String,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            keep_backend_running: default_keep_backend_running(),
            language: default_language(),
            enable_local_model: false,
            local_model: String::new(),
            local_model_endpoint: default_local_model_endpoint(),
        }
    }
}

fn default_keep_backend_running() -> bool {
    true
}

fn default_language() -> String {
    "zh-CN".to_string()
}

fn default_local_model_endpoint() -> String {
    "http://localhost:11434".to_string()
}

/// 获取设置文件路径
fn get_settings_path() -> Option<PathBuf> {
    dirs::home_dir().map(|home| home.join(".localbrisk").join("App_Data").join("settings.yaml"))
}

/// 从配置文件加载设置
pub fn load() -> AppSettings {
    get_settings_path()
        .and_then(|path| {
            if path.exists() {
                fs::read_to_string(&path)
                    .ok()
                    .and_then(|content| serde_yaml::from_str(&content).ok())
            } else {
                None
            }
        })
        .inspect(|settings| log(&format!("已从配置文件加载设置: {:?}", settings)))
        .unwrap_or_else(|| {
            log("使用默认设置");
            AppSettings::default()
        })
}

/// 保存设置到配置文件
pub fn save(settings: &AppSettings) -> Result<(), String> {
    let path = get_settings_path().ok_or("无法获取配置文件路径")?;

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("创建配置目录失败: {}", e))?;
    }

    let content = serde_yaml::to_string(settings).map_err(|e| format!("序列化设置失败: {}", e))?;
    fs::write(&path, content).map_err(|e| format!("写入配置文件失败: {}", e))?;

    log(&format!("设置已保存到: {:?}", path));
    Ok(())
}

/// 初始化全局设置状态
pub fn init_global_state() {
    let settings = load();
    KEEP_BACKEND_RUNNING.store(settings.keep_backend_running, Ordering::SeqCst);
    log(&format!(
        "已加载设置: keepBackendRunning = {}",
        settings.keep_backend_running
    ));
}

/// 获取全局 keep_backend_running 状态
pub fn get_keep_backend_running() -> bool {
    KEEP_BACKEND_RUNNING.load(Ordering::SeqCst)
}

/// 设置全局 keep_backend_running 状态并保存
pub fn set_keep_backend_running(keep: bool) -> Result<(), String> {
    KEEP_BACKEND_RUNNING.store(keep, Ordering::SeqCst);
    log(&format!("设置 keepBackendRunning = {}", keep));

    let mut settings = load();
    settings.keep_backend_running = keep;
    save(&settings)
}
