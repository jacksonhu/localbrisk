//! 后端服务模块 - 管理后端进程的启动和停止

use std::time::Duration;

const HEALTH_URL: &str = "http://127.0.0.1:8765/health";

/// 后端进程 PID 的全局存储（用于在退出时终止整个进程树）
#[cfg(not(debug_assertions))]
pub static BACKEND_PID: std::sync::OnceLock<std::sync::Mutex<Option<u32>>> =
    std::sync::OnceLock::new();

/// 检查后端服务是否已在运行
#[cfg(not(debug_assertions))]
fn is_running() -> bool {
    use std::net::TcpStream;
    use std::process::Command;

    use crate::logger::log;

    const BACKEND_ADDR: &str = "127.0.0.1:8765";

    // 方法1：尝试连接端口（快速检查）
    if TcpStream::connect_timeout(&BACKEND_ADDR.parse().unwrap(), Duration::from_millis(500))
        .is_err()
    {
        return false;
    }

    log("端口 8765 已被占用，后端可能已在运行");

    // 方法2：发送 HTTP 请求确认是我们的后端服务
    match Command::new("curl")
        .args([
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "--connect-timeout",
            "1",
            HEALTH_URL,
        ])
        .output()
    {
        Ok(output) => {
            let status = String::from_utf8_lossy(&output.stdout);
            if status.trim() == "200" {
                log("后端健康检查通过，服务已在运行");
                return true;
            }
        }
        Err(e) => {
            log(&format!("健康检查失败: {}", e));
        }
    }

    false
}

/// 在 Release 模式下启动后端服务
#[cfg(not(debug_assertions))]
pub fn start(app_handle: tauri::AppHandle) {
    use tauri_plugin_shell::process::CommandEvent;
    use tauri_plugin_shell::ShellExt;

    use crate::logger::log;

    // 初始化全局后端进程 PID 存储
    let _ = BACKEND_PID.get_or_init(|| std::sync::Mutex::new(None));

    // 先检查后端服务是否已经在运行
    log("检查后端服务是否已在运行...");
    if is_running() {
        log("后端服务已在运行，跳过启动");
        return;
    }

    log("正在启动后端服务 (Release 模式)...");

    std::thread::spawn(move || {
        let command = match app_handle.shell().sidecar("localbrisk-backend") {
            Ok(cmd) => cmd,
            Err(e) => {
                log(&format!("创建 sidecar 命令失败: {}", e));
                eprintln!("创建 sidecar 命令失败: {}", e);
                return;
            }
        };

        log("Sidecar 命令创建成功");

        match command.spawn() {
            Ok((mut rx, child)) => {
                let pid = child.pid();
                log(&format!("后端进程已启动, PID: {}", pid));

                // 存储 PID，以便退出时终止整个进程树
                if let Some(mutex) = BACKEND_PID.get() {
                    if let Ok(mut guard) = mutex.lock() {
                        *guard = Some(pid);
                    }
                }

                // 在后台线程处理输出
                tauri::async_runtime::spawn(async move {
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => {
                                let output = String::from_utf8_lossy(&line);
                                println!("[Backend] {}", output);
                                log(&format!("[Backend stdout] {}", output));
                            }
                            CommandEvent::Stderr(line) => {
                                let output = String::from_utf8_lossy(&line);
                                eprintln!("[Backend Error] {}", output);
                                log(&format!("[Backend stderr] {}", output));
                            }
                            CommandEvent::Error(err) => {
                                eprintln!("[Backend] 错误: {}", err);
                                log(&format!("[Backend error] {}", err));
                            }
                            CommandEvent::Terminated(payload) => {
                                log(&format!(
                                    "[Backend] 进程终止, code: {:?}, signal: {:?}",
                                    payload.code, payload.signal
                                ));
                                break;
                            }
                            _ => {}
                        }
                    }
                });
            }
            Err(e) => {
                log(&format!("启动后端失败: {}", e));
                eprintln!("启动后端失败: {}", e);
            }
        }
    });
}

/// 在 Release 模式下停止后端服务
#[cfg(not(debug_assertions))]
pub fn stop() {
    use std::process::Command;
    use std::sync::atomic::Ordering;

    use crate::logger::log;

    if crate::settings::KEEP_BACKEND_RUNNING.load(Ordering::SeqCst) {
        log("保持后端服务运行，可通过 API 继续访问");
        return;
    }

    log("正在关闭后端服务...");

    if let Some(mutex) = BACKEND_PID.get() {
        if let Ok(guard) = mutex.lock() {
            if let Some(pid) = *guard {
                log(&format!("终止后端进程树, 父 PID: {}", pid));

                // 首先终止子进程
                let _ = Command::new("pkill").args(["-P", &pid.to_string()]).output();

                // 然后终止父进程
                let _ = Command::new("kill").args(["-9", &pid.to_string()]).output();

                log("后端服务已关闭");
            }
        }
    }
}

/// 异步检查后端健康状态
#[tauri::command]
pub async fn check_backend_health() -> Result<String, String> {
    let client = reqwest::Client::new();
    match client
        .get(HEALTH_URL)
        .timeout(Duration::from_secs(2))
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
        Err(e) => Err(format!("Failed to connect to backend: {}", e)),
    }
}
