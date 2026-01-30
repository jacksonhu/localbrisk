// LocalBrisk - Tauri 主程序入口
// 负责窗口管理、系统原生集成

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::PathBuf;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
use serde::{Deserialize, Serialize};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    Emitter, Manager,
};

/// 全局设置：是否在退出时保持后端运行
static KEEP_BACKEND_RUNNING: AtomicBool = AtomicBool::new(true);

/// 后端进程 PID 的全局存储（用于在退出时终止整个进程树）
#[cfg(not(debug_assertions))]
static BACKEND_PID: std::sync::OnceLock<std::sync::Mutex<Option<u32>>> = std::sync::OnceLock::new();

/// 应用设置结构 - 统一管理所有配置项
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AppSettings {
    /// 是否在退出时保持后端运行
    #[serde(default = "default_keep_backend_running")]
    keep_backend_running: bool,
    
    /// 界面语言
    #[serde(default = "default_language")]
    language: String,
    
    /// 是否启用本地模型
    #[serde(default)]
    enable_local_model: bool,
    
    /// 选择的本地模型名称
    #[serde(default)]
    local_model: String,
    
    /// 本地模型服务端点
    #[serde(default = "default_local_model_endpoint")]
    local_model_endpoint: String,
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
    dirs::home_dir().map(|home| {
        home.join(".localbrisk").join("App_Data").join("settings.yaml")
    })
}

/// 从配置文件加载设置
fn load_settings() -> AppSettings {
    if let Some(path) = get_settings_path() {
        if path.exists() {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(settings) = serde_yaml::from_str::<AppSettings>(&content) {
                    log_to_file(&format!("已从配置文件加载设置: {:?}", settings));
                    return settings;
                }
            }
        }
    }
    log_to_file("使用默认设置");
    AppSettings::default()
}

/// 保存设置到配置文件
fn save_settings(settings: &AppSettings) -> Result<(), String> {
    if let Some(path) = get_settings_path() {
        // 确保目录存在
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("创建配置目录失败: {}", e))?;
        }
        
        // 序列化并保存
        let content = serde_yaml::to_string(settings)
            .map_err(|e| format!("序列化设置失败: {}", e))?;
        
        fs::write(&path, content)
            .map_err(|e| format!("写入配置文件失败: {}", e))?;
        
        log_to_file(&format!("设置已保存到: {:?}", path));
        Ok(())
    } else {
        Err("无法获取配置文件路径".to_string())
    }
}

/// 简单日志函数
fn log_to_file(message: &str) {
    if let Some(home) = dirs::home_dir() {
        let log_dir = home.join("Library").join("Logs").join("LocalBrisk");
        let _ = fs::create_dir_all(&log_dir);
        let log_file = log_dir.join("app.log");
        if let Ok(mut file) = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_file)
        {
            let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
            let _ = writeln!(file, "[{}] {}", timestamp, message);
        }
    }
}

/// 文件信息结构
#[derive(Debug, Serialize, Deserialize)]
pub struct FileInfo {
    pub name: String,
    pub is_directory: bool,
    pub size: Option<u64>,
    pub modified_time: Option<String>,
    pub created_time: Option<String>,
    pub readonly: bool,
}

/// 获取应用信息
#[tauri::command]
fn get_app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "LocalBrisk",
        "version": "0.1.0",
        "description": "本地化全能 AI 智能体工作站"
    })
}

/// 健康检查命令
#[tauri::command]
fn health_check() -> String {
    "OK".to_string()
}

/// 获取后端服务状态
#[tauri::command]
async fn check_backend_health() -> Result<String, String> {
    let client = reqwest::Client::new();
    match client.get("http://127.0.0.1:8765/health")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await 
    {
        Ok(resp) => {
            if resp.status().is_success() {
                Ok("Backend is healthy".to_string())
            } else {
                Err(format!("Backend returned status: {}", resp.status()))
            }
        }
        Err(e) => Err(format!("Failed to connect to backend: {}", e))
    }
}

/// 列出目录内容
#[tauri::command]
fn list_directory(path: String) -> Result<Vec<FileInfo>, String> {
    let dir_path = PathBuf::from(&path);
    
    if !dir_path.exists() {
        return Err(format!("Path does not exist: {}", path));
    }
    
    if !dir_path.is_dir() {
        return Err(format!("Path is not a directory: {}", path));
    }
    
    let mut files: Vec<FileInfo> = Vec::new();
    
    match fs::read_dir(&dir_path) {
        Ok(entries) => {
            for entry in entries {
                if let Ok(entry) = entry {
                    let file_name = entry.file_name().to_string_lossy().to_string();
                    
                    // 跳过隐藏文件（以.开头的文件）
                    if file_name.starts_with('.') {
                        continue;
                    }
                    
                    let metadata = entry.metadata();
                    
                    let (is_dir, size, modified, created, readonly) = match metadata {
                        Ok(meta) => {
                            let modified_time = meta.modified().ok().map(|t| {
                                let datetime: chrono::DateTime<chrono::Utc> = t.into();
                                datetime.to_rfc3339()
                            });
                            let created_time = meta.created().ok().map(|t| {
                                let datetime: chrono::DateTime<chrono::Utc> = t.into();
                                datetime.to_rfc3339()
                            });
                            (
                                meta.is_dir(),
                                if meta.is_file() { Some(meta.len()) } else { None },
                                modified_time,
                                created_time,
                                meta.permissions().readonly(),
                            )
                        }
                        Err(_) => (false, None, None, None, false),
                    };
                    
                    files.push(FileInfo {
                        name: file_name,
                        is_directory: is_dir,
                        size,
                        modified_time: modified,
                        created_time: created,
                        readonly,
                    });
                }
            }
            
            // 排序：文件夹优先，然后按名称排序
            files.sort_by(|a, b| {
                match (a.is_directory, b.is_directory) {
                    (true, false) => std::cmp::Ordering::Less,
                    (false, true) => std::cmp::Ordering::Greater,
                    _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
                }
            });
            
            Ok(files)
        }
        Err(e) => Err(format!("Failed to read directory: {}", e)),
    }
}

/// 创建目录
#[tauri::command]
fn create_directory(path: String) -> Result<(), String> {
    let dir_path = PathBuf::from(&path);
    
    if dir_path.exists() {
        return Err(format!("Path already exists: {}", path));
    }
    
    fs::create_dir_all(&dir_path)
        .map_err(|e| format!("Failed to create directory: {}", e))
}

/// 删除文件或目录
#[tauri::command]
fn delete_path(path: String) -> Result<(), String> {
    let target_path = PathBuf::from(&path);
    
    if !target_path.exists() {
        return Err(format!("Path does not exist: {}", path));
    }
    
    if target_path.is_dir() {
        fs::remove_dir_all(&target_path)
            .map_err(|e| format!("Failed to delete directory: {}", e))
    } else {
        fs::remove_file(&target_path)
            .map_err(|e| format!("Failed to delete file: {}", e))
    }
}

/// 检查路径是否存在
#[tauri::command]
fn path_exists(path: String) -> bool {
    PathBuf::from(&path).exists()
}

/// 获取文件信息
#[tauri::command]
fn get_file_info(path: String) -> Result<FileInfo, String> {
    let file_path = PathBuf::from(&path);
    
    if !file_path.exists() {
        return Err(format!("Path does not exist: {}", path));
    }
    
    let file_name = file_path
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    
    let metadata = fs::metadata(&file_path)
        .map_err(|e| format!("Failed to get metadata: {}", e))?;
    
    let modified_time = metadata.modified().ok().map(|t| {
        let datetime: chrono::DateTime<chrono::Utc> = t.into();
        datetime.to_rfc3339()
    });
    let created_time = metadata.created().ok().map(|t| {
        let datetime: chrono::DateTime<chrono::Utc> = t.into();
        datetime.to_rfc3339()
    });
    
    Ok(FileInfo {
        name: file_name,
        is_directory: metadata.is_dir(),
        size: if metadata.is_file() { Some(metadata.len()) } else { None },
        modified_time,
        created_time,
        readonly: metadata.permissions().readonly(),
    })
}

/// 读取文件内容（文本）
#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read file: {}", e))
}

/// 写入文件内容（文本）
#[tauri::command]
fn write_text_file(path: String, content: String) -> Result<(), String> {
    fs::write(&path, content)
        .map_err(|e| format!("Failed to write file: {}", e))
}

/// 读取文件内容（二进制，返回 Base64）
#[tauri::command]
fn read_binary_file(path: String) -> Result<String, String> {
    use base64::{Engine as _, engine::general_purpose::STANDARD};
    
    let bytes = fs::read(&path)
        .map_err(|e| format!("Failed to read file: {}", e))?;
    
    Ok(STANDARD.encode(&bytes))
}

/// 设置是否在退出时保持后端运行
#[tauri::command]
fn set_keep_backend_running(keep: bool) -> Result<(), String> {
    KEEP_BACKEND_RUNNING.store(keep, Ordering::SeqCst);
    log_to_file(&format!("设置 keepBackendRunning = {}", keep));
    
    // 加载现有设置并更新
    let mut settings = load_settings();
    settings.keep_backend_running = keep;
    save_settings(&settings)
}

/// 获取是否在退出时保持后端运行
#[tauri::command]
fn get_keep_backend_running() -> bool {
    KEEP_BACKEND_RUNNING.load(Ordering::SeqCst)
}

/// 获取所有应用设置
#[tauri::command]
fn get_app_settings() -> AppSettings {
    let settings = load_settings();
    log_to_file(&format!("获取应用设置: {:?}", settings));
    settings
}

/// 保存所有应用设置
#[tauri::command]
fn save_app_settings(settings: AppSettings) -> Result<(), String> {
    // 同步更新全局状态
    KEEP_BACKEND_RUNNING.store(settings.keep_backend_running, Ordering::SeqCst);
    log_to_file(&format!("保存应用设置: {:?}", settings));
    save_settings(&settings)
}

/// 同步检查后端服务是否已在运行（通过 HTTP 健康检查）
fn check_backend_running() -> bool {
    use std::net::TcpStream;
    use std::time::Duration;
    
    // 方法1：尝试连接端口（快速检查）
    if TcpStream::connect_timeout(
        &"127.0.0.1:8765".parse().unwrap(),
        Duration::from_millis(500)
    ).is_ok() {
        log_to_file("端口 8765 已被占用，后端可能已在运行");
        
        // 方法2：发送 HTTP 请求确认是我们的后端服务
        // 使用阻塞式 HTTP 请求
        match std::process::Command::new("curl")
            .args([
                "-s",
                "-o", "/dev/null",
                "-w", "%{http_code}",
                "--connect-timeout", "1",
                "http://127.0.0.1:8765/health"
            ])
            .output()
        {
            Ok(output) => {
                let status = String::from_utf8_lossy(&output.stdout);
                if status.trim() == "200" {
                    log_to_file("后端健康检查通过，服务已在运行");
                    return true;
                }
            }
            Err(e) => {
                log_to_file(&format!("健康检查失败: {}", e));
            }
        }
    }
    
    false
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .menu(|app| {
            // 创建应用菜单
            let app_submenu = Submenu::with_items(
                app,
                "LocalBrisk",
                true,
                &[
                    &MenuItem::with_id(app, "about", "About LocalBrisk", true, None::<&str>)?,
                    &PredefinedMenuItem::separator(app)?,
                    &MenuItem::with_id(app, "settings", "Settings...", true, Some("CmdOrCtrl+,"))?,
                    &PredefinedMenuItem::separator(app)?,
                    &PredefinedMenuItem::hide(app, Some("Hide LocalBrisk"))?,
                    &PredefinedMenuItem::hide_others(app, Some("Hide Others"))?,
                    &PredefinedMenuItem::show_all(app, Some("Show All"))?,
                    &PredefinedMenuItem::separator(app)?,
                    &PredefinedMenuItem::quit(app, Some("Quit LocalBrisk"))?,
                ],
            )?;

            // 编辑菜单
            let edit_submenu = Submenu::with_items(
                app,
                "Edit",
                true,
                &[
                    &PredefinedMenuItem::undo(app, Some("Undo"))?,
                    &PredefinedMenuItem::redo(app, Some("Redo"))?,
                    &PredefinedMenuItem::separator(app)?,
                    &PredefinedMenuItem::cut(app, Some("Cut"))?,
                    &PredefinedMenuItem::copy(app, Some("Copy"))?,
                    &PredefinedMenuItem::paste(app, Some("Paste"))?,
                    &PredefinedMenuItem::select_all(app, Some("Select All"))?,
                ],
            )?;

            // 窗口菜单
            let window_submenu = Submenu::with_items(
                app,
                "Window",
                true,
                &[
                    &PredefinedMenuItem::minimize(app, Some("Minimize"))?,
                    &PredefinedMenuItem::maximize(app, Some("Maximize"))?,
                    &PredefinedMenuItem::separator(app)?,
                    &PredefinedMenuItem::close_window(app, Some("Close Window"))?,
                ],
            )?;

            // 帮助菜单
            let help_submenu = Submenu::with_items(
                app,
                "Help",
                true,
                &[
                    &MenuItem::with_id(app, "documentation", "Documentation", true, None::<&str>)?,
                    &MenuItem::with_id(app, "feedback", "Report Issue", true, None::<&str>)?,
                    &PredefinedMenuItem::separator(app)?,
                    &MenuItem::with_id(app, "devtools", "Toggle Developer Tools", true, Some("CmdOrCtrl+Shift+I"))?,
                ],
            )?;

            Menu::with_items(app, &[&app_submenu, &edit_submenu, &window_submenu, &help_submenu])
        })
        .on_menu_event(|app, event| {
            println!("菜单事件触发: {:?}", event.id());
            match event.id().as_ref() {
                "settings" => {
                    println!("点击了设置菜单");
                    // 发送事件到前端主窗口打开设置弹窗
                    if let Some(window) = app.get_webview_window("main") {
                        match window.emit("open-settings", ()) {
                            Ok(_) => println!("已发送 open-settings 事件到主窗口"),
                            Err(e) => println!("发送事件失败: {:?}", e),
                        }
                    } else {
                        println!("未找到主窗口");
                    }
                }
                "about" => {
                    println!("点击了关于菜单");
                    // 发送事件到前端主窗口打开关于弹窗
                    if let Some(window) = app.get_webview_window("main") {
                        match window.emit("open-about", ()) {
                            Ok(_) => println!("已发送 open-about 事件到主窗口"),
                            Err(e) => println!("发送事件失败: {:?}", e),
                        }
                    } else {
                        println!("未找到主窗口");
                    }
                }
                "documentation" => {
                    // 打开文档链接
                    let _ = tauri::async_runtime::spawn(async {
                        let _ = open::that("https://github.com/localbrisk/localbrisk");
                    });
                }
                "feedback" => {
                    // 打开反馈链接
                    let _ = tauri::async_runtime::spawn(async {
                        let _ = open::that("https://github.com/localbrisk/localbrisk/issues");
                    });
                }
                "devtools" => {
                    // 打开/关闭开发者工具
                    if let Some(window) = app.get_webview_window("main") {
                        if window.is_devtools_open() {
                            window.close_devtools();
                        } else {
                            window.open_devtools();
                        }
                    }
                }
                _ => {}
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_app_info,
            health_check,
            check_backend_health,
            list_directory,
            create_directory,
            delete_path,
            path_exists,
            get_file_info,
            read_text_file,
            write_text_file,
            read_binary_file,
            set_keep_backend_running,
            get_keep_backend_running,
            get_app_settings,
            save_app_settings
        ])
        .setup(|app| {
            log_to_file("========== LocalBrisk 启动 ==========");
            log_to_file(&format!("Tauri version: {}", tauri::VERSION));
            
            // 从配置文件加载设置
            let settings = load_settings();
            KEEP_BACKEND_RUNNING.store(settings.keep_backend_running, Ordering::SeqCst);
            log_to_file(&format!("已加载设置: keepBackendRunning = {}", settings.keep_backend_running));
            
            // 只在 Release 模式下启动后端 sidecar
            // 开发模式下由 dev.sh 手动启动后端
            #[cfg(not(debug_assertions))]
            {
                // 初始化全局后端进程 PID 存储
                let _ = BACKEND_PID.get_or_init(|| std::sync::Mutex::new(None));
                
                // 先检查后端服务是否已经在运行
                log_to_file("检查后端服务是否已在运行...");
                let backend_already_running = check_backend_running();
                
                if backend_already_running {
                    log_to_file("后端服务已在运行，跳过启动");
                } else {
                    log_to_file("正在启动后端服务 (Release 模式)...");
                    let app_handle = app.handle().clone();
                    
                    std::thread::spawn(move || {
                        use tauri_plugin_shell::ShellExt;
                        
                        match app_handle.shell().sidecar("localbrisk-backend") {
                            Ok(command) => {
                                log_to_file("Sidecar 命令创建成功");
                                
                                match command.spawn() {
                                    Ok((mut rx, child)) => {
                                        let pid = child.pid();
                                        log_to_file(&format!("后端进程已启动, PID: {}", pid));
                                        
                                        // 存储 PID，以便退出时终止整个进程树
                                        if let Some(mutex) = BACKEND_PID.get() {
                                            if let Ok(mut guard) = mutex.lock() {
                                                *guard = Some(pid);
                                            }
                                        }
                                        
                                        // 在后台线程处理输出
                                        tauri::async_runtime::spawn(async move {
                                            use tauri_plugin_shell::process::CommandEvent;
                                            
                                            while let Some(event) = rx.recv().await {
                                                match event {
                                                    CommandEvent::Stdout(line) => {
                                                        let output = String::from_utf8_lossy(&line);
                                                        println!("[Backend] {}", output);
                                                        log_to_file(&format!("[Backend stdout] {}", output));
                                                    }
                                                    CommandEvent::Stderr(line) => {
                                                        let output = String::from_utf8_lossy(&line);
                                                        eprintln!("[Backend Error] {}", output);
                                                        log_to_file(&format!("[Backend stderr] {}", output));
                                                    }
                                                    CommandEvent::Error(err) => {
                                                        eprintln!("[Backend] 错误: {}", err);
                                                        log_to_file(&format!("[Backend error] {}", err));
                                                    }
                                                    CommandEvent::Terminated(payload) => {
                                                        log_to_file(&format!("[Backend] 进程终止, code: {:?}, signal: {:?}", 
                                                            payload.code, payload.signal));
                                                        break;
                                                    }
                                                    _ => {}
                                                }
                                            }
                                        });
                                    }
                                    Err(e) => {
                                        log_to_file(&format!("启动后端失败: {}", e));
                                        eprintln!("启动后端失败: {}", e);
                                    }
                                }
                            }
                            Err(e) => {
                                log_to_file(&format!("创建 sidecar 命令失败: {}", e));
                                eprintln!("创建 sidecar 命令失败: {}", e);
                            }
                        }
                    });
                }
            }
            
            #[cfg(debug_assertions)]
            {
                log_to_file("开发模式: 跳过 sidecar 启动，由 dev.sh 管理后端");
            }
            
            // 应用启动时的初始化逻辑
            let window = app.get_webview_window("main");
            
            match &window {
                Some(w) => {
                    log_to_file(&format!("主窗口已创建: {:?}", w.label()));
                    
                    // 获取窗口 URL
                    if let Ok(url) = w.url() {
                        log_to_file(&format!("窗口 URL: {}", url));
                    }
                }
                None => {
                    log_to_file("错误: 主窗口未创建！");
                }
            }
            
            #[cfg(debug_assertions)]
            {
                // 开发模式下打开开发者工具
                if let Some(w) = window {
                    w.open_devtools();
                    log_to_file("开发模式: 已打开开发者工具");
                }
            }
            
            log_to_file("LocalBrisk 启动完成！");
            println!("LocalBrisk 启动成功！");
            Ok(())
        })
        .on_window_event(|_window, event| {
            // 监听窗口关闭事件
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let keep_running = KEEP_BACKEND_RUNNING.load(Ordering::SeqCst);
                log_to_file(&format!("窗口关闭请求, keepBackendRunning = {}", keep_running));
                
                #[cfg(not(debug_assertions))]
                {
                    if !keep_running {
                        // 用户选择不保持后端运行，终止后端进程树
                        log_to_file("正在关闭后端服务...");
                        if let Some(mutex) = BACKEND_PID.get() {
                            if let Ok(guard) = mutex.lock() {
                                if let Some(pid) = *guard {
                                    // 使用 pkill 终止整个进程树（通过父进程 PID）
                                    // -P 参数表示终止指定父进程的所有子进程
                                    log_to_file(&format!("终止后端进程树, 父 PID: {}", pid));
                                    
                                    // 首先终止子进程
                                    let _ = std::process::Command::new("pkill")
                                        .args(["-P", &pid.to_string()])
                                        .output();
                                    
                                    // 然后终止父进程
                                    let _ = std::process::Command::new("kill")
                                        .args(["-9", &pid.to_string()])
                                        .output();
                                    
                                    log_to_file("后端服务已关闭");
                                }
                            }
                        }
                    } else {
                        log_to_file("保持后端服务运行，可通过 API 继续访问");
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
