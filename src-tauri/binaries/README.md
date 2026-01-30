# Tauri Binaries 目录

此目录用于存放打包后的 Python 后端可执行文件。

## 文件命名规则

Tauri 要求 sidecar 二进制文件使用平台三元组命名：

- **macOS (Intel)**: `localbrisk-backend-x86_64-apple-darwin`
- **macOS (Apple Silicon)**: `localbrisk-backend-aarch64-apple-darwin`
- **Windows**: `localbrisk-backend-x86_64-pc-windows-msvc.exe`
- **Linux**: `localbrisk-backend-x86_64-unknown-linux-gnu`

## 获取当前平台三元组

```bash
rustc -vV | grep host | cut -d ' ' -f2
```

## 构建方法

运行项目根目录的构建脚本会自动将 Python 后端打包并复制到此目录：

```bash
# macOS/Linux
./build.sh

# Windows
build.bat
```
