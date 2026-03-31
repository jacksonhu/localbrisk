# LocalBrisk 开发指南

[English](DEVELOPMENT.md) | **中文**

## 项目结构

```
LocalBrisk/
├── frontend/               # 前端 UI 代码
│   ├── src/                # Vue 3 前端源码
│   │   ├── components/     # UI 组件
│   │   ├── views/          # 页面视图
│   │   ├── services/       # API 服务
│   │   │   ├── api.ts      # Python 后端 API
│   │   │   └── tauri.ts    # Tauri 命令调用
│   │   ├── types/          # TypeScript 类型定义
│   │   └── styles/         # 全局样式
│   ├── public/             # 静态资源
│   ├── index.html          # 入口 HTML
│   ├── package.json        # 前端依赖配置
│   ├── vite.config.ts      # Vite 配置
│   ├── tsconfig.json       # TypeScript 配置
│   ├── tailwind.config.js  # Tailwind CSS 配置
│   └── postcss.config.js   # PostCSS 配置
├── src-tauri/              # Tauri (Rust) 桌面外壳
│   ├── src/
│   │   └── main.rs         # Rust 主程序（含 Sidecar 管理）
│   ├── binaries/           # 打包后的 Python 后端
│   ├── capabilities/       # Tauri 权限配置
│   ├── Cargo.toml
│   └── tauri.conf.json     # Tauri 配置
├── backend/                # Python FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 端点
│   │   ├── core/           # 核心配置
│   │   └── models/         # 数据模型
│   ├── main.py             # FastAPI 入口
│   ├── run.py              # 打包入口
│   ├── localbrisk-backend.spec  # PyInstaller 配置
│   └── requirements.txt
├── build.sh                # macOS/Linux 构建脚本
├── build.bat               # Windows 构建脚本
└── dev.sh                  # 开发启动脚本
```

## 环境要求

- **Node.js** >= 18
- **Rust** >= 1.70
- **Python** >= 3.10

## 快速开始

### 1. 安装前端依赖

```bash
cd frontend
npm install
```

### 2. 安装 Python 依赖

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 3. 开发模式

**方式一：分别启动（推荐开发时使用）**

```bash
# 终端 1: 启动 Python 后端
cd backend
source venv/bin/activate
python main.py

# 终端 2: 启动 Tauri 前端
cd frontend
npm run tauri:dev
```

**方式二：一键启动**

```bash
# macOS/Linux
./dev.sh

# 或使用 npm (在 frontend 目录下)
cd frontend
npm run fulldev
```

### 4. 纯前端开发（不需要后端）

```bash
cd frontend
npm run dev
```

访问 http://localhost:1420

## 构建发布

### 一键打包

```bash
# macOS/Linux
./build.sh

# Windows
build.bat
```

### 分步构建

```bash
# 1. 打包 Python 后端
cd backend
source venv/bin/activate
pyinstaller --clean --noconfirm localbrisk-backend.spec

# 2. 复制到 Tauri binaries 目录
mkdir -p ../src-tauri/binaries
cp dist/localbrisk-backend ../src-tauri/binaries/localbrisk-backend-$(rustc -vV | grep host | cut -d ' ' -f2)

# 3. 构建 Tauri 应用
cd ../frontend
npm run tauri:build
```

### 生成应用图标

```bash
cd frontend
npm run tauri:icon
```

## 构建产物位置

- **macOS**: `src-tauri/target/release/bundle/macos/`
- **macOS DMG**: `src-tauri/target/release/bundle/dmg/`
- **Windows MSI**: `src-tauri/target/release/bundle/msi/`
- **Windows NSIS**: `src-tauri/target/release/bundle/nsis/`
- **Linux AppImage**: `src-tauri/target/release/bundle/appimage/`
- **Linux DEB**: `src-tauri/target/release/bundle/deb/`

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| UI 层 | Vue 3 + Vite + Tailwind CSS | 响应式前端界面 |
| 桌面外壳 | Tauri 2.0 (Rust) | 窗口管理、Sidecar 调度 |
| 后端服务 | Python FastAPI | 本地 Web 服务 |
| 数据处理 | Polars | 高性能数据分析 |
| 存储 | DuckDB | 本地向量/结构化存储 |
| 打包 | PyInstaller + Tauri Bundler | 跨平台打包 |

## 架构说明

### Sidecar 机制

LocalBrisk 使用 Tauri 的 Sidecar 机制来管理 Python 后端：

1. **启动流程**：Tauri 应用启动时自动调用打包好的 Python 可执行文件
2. **通信方式**：前端通过 HTTP 请求与 Python FastAPI 通信（端口 8765）
3. **生命周期**：窗口关闭时自动终止 Python 进程

### 前后端通信

```
┌─────────────────┐     HTTP      ┌─────────────────┐
│   Vue 3 前端    │ ──────────────▶ │  Python FastAPI │
│  (localhost:1420)│ ◀────────────── │  (localhost:8765)│
└─────────────────┘               └─────────────────┘
         │                                  ▲
         │ Tauri IPC                        │
         ▼                                  │
┌─────────────────┐    spawn/kill   ┌─────────────────┐
│   Rust Tauri    │ ───────────────▶ │  Python Sidecar │
│   (主进程)       │                  │  (子进程)        │
└─────────────────┘                  └─────────────────┘
```

## 常见问题

### Q: Tauri 开发模式下后端连接失败？

A: 确保先启动 Python 后端服务（端口 8765），再启动 Tauri 开发模式。

### Q: PyInstaller 打包失败？

A: 检查 Python 版本（需要 3.10+）和依赖是否正确安装。某些依赖可能需要添加到 `hiddenimports` 中。

### Q: macOS 构建提示签名问题？

A: 开发测试时可以忽略签名。正式发布需要 Apple Developer 证书。
