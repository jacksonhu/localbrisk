@echo off
REM LocalBrisk 构建脚本 - Windows
REM 用于打包 Python 后端并构建 Tauri 应用

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%

echo ======================================
echo LocalBrisk 构建脚本
echo ======================================

REM 检查必要工具
echo 检查构建环境...

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 Node.js，请先安装 Node.js ^>= 18
    exit /b 1
)

where cargo >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 Rust/Cargo，请先安装 Rust
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python ^>= 3.10
    exit /b 1
)

echo √ 构建环境检查通过

REM 安装前端依赖
echo.
echo 安装依赖...
cd /d "%PROJECT_ROOT%"
call npm install
echo √ 根目录依赖安装完成

cd /d "%PROJECT_ROOT%frontend"
call npm install
echo √ 前端依赖安装完成

REM 构建 Python 后端
echo.
echo 构建 Python 后端...
cd /d "%PROJECT_ROOT%backend"

REM 创建虚拟环境（如果不存在）
if not exist "venv" (
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
pip install -r requirements.txt
pip install pyinstaller

REM 使用 PyInstaller 打包
echo 使用 PyInstaller 打包...
pyinstaller --clean --noconfirm localbrisk-backend.spec

REM 获取目标三元组
for /f "tokens=2" %%i in ('rustc -vV ^| findstr host') do set TARGET_TRIPLE=%%i

REM 复制到 Tauri binaries 目录
set TAURI_BINARIES_DIR=%PROJECT_ROOT%src-tauri\binaries
if not exist "%TAURI_BINARIES_DIR%" mkdir "%TAURI_BINARIES_DIR%"

if exist "dist\localbrisk-backend.exe" (
    copy /y "dist\localbrisk-backend.exe" "%TAURI_BINARIES_DIR%\localbrisk-backend-%TARGET_TRIPLE%.exe"
    echo √ Python 后端打包完成: localbrisk-backend-%TARGET_TRIPLE%.exe
) else (
    echo 错误: PyInstaller 打包失败
    exit /b 1
)

call deactivate

REM 构建 Tauri 应用
echo.
echo 构建 Tauri 应用...
cd /d "%PROJECT_ROOT%"
call npx tauri build

echo.
echo ======================================
echo 构建完成！
echo ======================================
echo.
echo 构建产物位置:
echo   Windows: src-tauri\target\release\bundle\msi\
echo   NSIS:    src-tauri\target\release\bundle\nsis\
echo.

endlocal
