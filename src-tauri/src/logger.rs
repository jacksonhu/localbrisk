//! 日志模块 - 简单的文件日志

use std::fs;
use std::io::Write;
use std::path::PathBuf;

/// 获取日志目录
fn get_log_dir() -> Option<PathBuf> {
    dirs::home_dir().map(|home| home.join("Library").join("Logs").join("LocalBrisk"))
}

/// 写入日志
pub fn log(message: &str) {
    if let Some(log_dir) = get_log_dir() {
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

/// 日志宏 - 简化日志调用
#[macro_export]
macro_rules! app_log {
    ($($arg:tt)*) => {
        $crate::logger::log(&format!($($arg)*))
    };
}
