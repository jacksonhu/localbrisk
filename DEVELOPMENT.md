# LocalBrisk Development Guide

[English](DEVELOPMENT.md) | [中文](DEVELOPMENT_zh.md)

## Project Structure

```
LocalBrisk/
├── frontend/               # Frontend UI code
│   ├── src/                # Vue 3 source
│   │   ├── components/     # UI components
│   │   ├── views/          # Page views
│   │   ├── services/       # API services
│   │   │   ├── api.ts      # Python backend API
│   │   │   └── tauri.ts    # Tauri command invocations
│   │   ├── types/          # TypeScript type definitions
│   │   └── styles/         # Global styles
│   ├── public/             # Static assets
│   ├── index.html          # Entry HTML
│   ├── package.json        # Frontend dependencies
│   ├── vite.config.ts      # Vite config
│   ├── tsconfig.json       # TypeScript config
│   ├── tailwind.config.js  # Tailwind CSS config
│   └── postcss.config.js   # PostCSS config
├── src-tauri/              # Tauri (Rust) desktop shell
│   ├── src/
│   │   └── main.rs         # Rust main entry (incl. Sidecar management)
│   ├── binaries/           # Packaged Python backend
│   ├── capabilities/       # Tauri permission config
│   ├── Cargo.toml
│   └── tauri.conf.json     # Tauri config
├── backend/                # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core configuration
│   │   └── models/         # Data models
│   ├── main.py             # FastAPI entry
│   ├── run.py              # Packaging entry
│   ├── localbrisk-backend.spec  # PyInstaller config
│   └── requirements.txt
├── build.sh                # macOS/Linux build script
├── build.bat               # Windows build script
└── dev.sh                  # Development launch script
```

## Prerequisites

- **Node.js** >= 18
- **Rust** >= 1.70
- **Python** >= 3.10

## Quick Start

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2. Install Python Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 3. Development Mode

**Option 1: Start separately (recommended for development)**

```bash
# Terminal 1: Start Python backend
cd backend
source venv/bin/activate
python main.py

# Terminal 2: Start Tauri frontend
cd frontend
npm run tauri:dev
```

**Option 2: One-click start**

```bash
# macOS/Linux
./dev.sh

# Or using npm (in frontend directory)
cd frontend
npm run fulldev
```

### 4. Frontend-Only Development (no backend needed)

```bash
cd frontend
npm run dev
```

Visit http://localhost:1420

## Build for Release

### One-Click Build

```bash
# macOS/Linux
./build.sh

# Windows
build.bat
```

### Step-by-Step Build

```bash
# 1. Package Python backend
cd backend
source venv/bin/activate
pyinstaller --clean --noconfirm localbrisk-backend.spec

# 2. Copy to Tauri binaries directory
mkdir -p ../src-tauri/binaries
cp dist/localbrisk-backend ../src-tauri/binaries/localbrisk-backend-$(rustc -vV | grep host | cut -d ' ' -f2)

# 3. Build Tauri application
cd ../frontend
npm run tauri:build
```

### Generate App Icons

```bash
cd frontend
npm run tauri:icon
```

## Build Artifacts

- **macOS**: `src-tauri/target/release/bundle/macos/`
- **macOS DMG**: `src-tauri/target/release/bundle/dmg/`
- **Windows MSI**: `src-tauri/target/release/bundle/msi/`
- **Windows NSIS**: `src-tauri/target/release/bundle/nsis/`
- **Linux AppImage**: `src-tauri/target/release/bundle/appimage/`
- **Linux DEB**: `src-tauri/target/release/bundle/deb/`

## Tech Stack

| Layer | Technology | Description |
|-------|-----------|-------------|
| UI | Vue 3 + Vite + Tailwind CSS | Responsive frontend UI |
| Desktop Shell | Tauri 2.0 (Rust) | Window management, Sidecar scheduling |
| Backend | Python FastAPI | Local web service |
| Data Processing | Polars | High-performance data analysis |
| Storage | DuckDB | Local analytical storage |
| Packaging | PyInstaller + Tauri Bundler | Cross-platform packaging |

## Architecture

### Sidecar Mechanism

LocalBrisk uses Tauri's Sidecar mechanism to manage the Python backend:

1. **Startup**: Tauri app automatically launches the packaged Python executable on startup
2. **Communication**: Frontend communicates with Python FastAPI via HTTP (port 8765)
3. **Lifecycle**: Python process is automatically terminated when the window closes

### Frontend-Backend Communication

```
┌─────────────────┐     HTTP      ┌─────────────────┐
│   Vue 3 Frontend│ ──────────────▶ │  Python FastAPI │
│  (localhost:1420)│ ◀────────────── │  (localhost:8765)│
└─────────────────┘               └─────────────────┘
         │                                  ▲
         │ Tauri IPC                        │
         ▼                                  │
┌─────────────────┐    spawn/kill   ┌─────────────────┐
│   Rust Tauri    │ ───────────────▶ │  Python Sidecar │
│  (Main Process) │                  │  (Child Process) │
└─────────────────┘                  └─────────────────┘
```

## FAQ

### Q: Backend connection fails in Tauri dev mode?

A: Make sure to start the Python backend service (port 8765) before launching Tauri dev mode.

### Q: PyInstaller packaging fails?

A: Check Python version (3.10+ required) and ensure all dependencies are correctly installed. Some dependencies may need to be added to `hiddenimports`.

### Q: macOS build prompts signing issues?

A: You can ignore signing during development testing. Official releases require an Apple Developer certificate.
