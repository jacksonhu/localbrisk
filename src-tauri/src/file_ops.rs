//! 文件操作模块 - 文件系统相关的 Tauri 命令

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

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

impl FileInfo {
    /// 从路径元数据创建 FileInfo
    fn from_metadata(name: String, metadata: &fs::Metadata) -> Self {
        let modified_time = metadata.modified().ok().map(Self::format_time);
        let created_time = metadata.created().ok().map(Self::format_time);

        Self {
            name,
            is_directory: metadata.is_dir(),
            size: if metadata.is_file() {
                Some(metadata.len())
            } else {
                None
            },
            modified_time,
            created_time,
            readonly: metadata.permissions().readonly(),
        }
    }

    fn format_time(time: std::time::SystemTime) -> String {
        let datetime: chrono::DateTime<chrono::Utc> = time.into();
        datetime.to_rfc3339()
    }
}

/// 列出目录内容
#[tauri::command]
pub fn list_directory(path: String) -> Result<Vec<FileInfo>, String> {
    let dir_path = PathBuf::from(&path);

    if !dir_path.exists() {
        return Err(format!("Path does not exist: {}", path));
    }
    if !dir_path.is_dir() {
        return Err(format!("Path is not a directory: {}", path));
    }

    let mut files: Vec<FileInfo> = fs::read_dir(&dir_path)
        .map_err(|e| format!("Failed to read directory: {}", e))?
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let name = entry.file_name().to_string_lossy().to_string();
            // 跳过隐藏文件
            if name.starts_with('.') {
                return None;
            }
            entry
                .metadata()
                .ok()
                .map(|meta| FileInfo::from_metadata(name, &meta))
        })
        .collect();

    // 排序：文件夹优先，然后按名称排序
    files.sort_by(|a, b| match (a.is_directory, b.is_directory) {
        (true, false) => std::cmp::Ordering::Less,
        (false, true) => std::cmp::Ordering::Greater,
        _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
    });

    Ok(files)
}

/// 创建目录
#[tauri::command]
pub fn create_directory(path: String) -> Result<(), String> {
    let dir_path = PathBuf::from(&path);

    if dir_path.exists() {
        return Err(format!("Path already exists: {}", path));
    }

    fs::create_dir_all(&dir_path).map_err(|e| format!("Failed to create directory: {}", e))
}

/// 删除文件或目录
#[tauri::command]
pub fn delete_path(path: String) -> Result<(), String> {
    let target_path = PathBuf::from(&path);

    if !target_path.exists() {
        return Err(format!("Path does not exist: {}", path));
    }

    if target_path.is_dir() {
        fs::remove_dir_all(&target_path).map_err(|e| format!("Failed to delete directory: {}", e))
    } else {
        fs::remove_file(&target_path).map_err(|e| format!("Failed to delete file: {}", e))
    }
}

/// 检查路径是否存在
#[tauri::command]
pub fn path_exists(path: String) -> bool {
    PathBuf::from(&path).exists()
}

/// 获取文件信息
#[tauri::command]
pub fn get_file_info(path: String) -> Result<FileInfo, String> {
    let file_path = PathBuf::from(&path);

    if !file_path.exists() {
        return Err(format!("Path does not exist: {}", path));
    }

    let name = file_path
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();

    let metadata = fs::metadata(&file_path).map_err(|e| format!("Failed to get metadata: {}", e))?;

    Ok(FileInfo::from_metadata(name, &metadata))
}

/// 读取文件内容（文本）
#[tauri::command]
pub fn read_text_file(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| format!("Failed to read file: {}", e))
}

/// 写入文件内容（文本）
#[tauri::command]
pub fn write_text_file(path: String, content: String) -> Result<(), String> {
    fs::write(&path, content).map_err(|e| format!("Failed to write file: {}", e))
}

/// 读取文件内容（二进制，返回 Base64）
#[tauri::command]
pub fn read_binary_file(path: String) -> Result<String, String> {
    use base64::{engine::general_purpose::STANDARD, Engine as _};

    let bytes = fs::read(&path).map_err(|e| format!("Failed to read file: {}", e))?;
    Ok(STANDARD.encode(&bytes))
}
