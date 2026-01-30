#!/bin/bash
# LocalBrisk 构建脚本 - macOS/Linux
# 用于打包 Python 后端并构建 Tauri 应用

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "======================================"
echo "LocalBrisk 构建脚本"
echo "======================================"

# 检查必要工具
check_requirements() {
    echo "检查构建环境..."
    
    if ! command -v node &> /dev/null; then
        echo "错误: 未找到 Node.js，请先安装 Node.js >= 18"
        exit 1
    fi
    
    if ! command -v cargo &> /dev/null; then
        echo "错误: 未找到 Rust/Cargo，请先安装 Rust"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo "错误: 未找到 Python3，请先安装 Python >= 3.10"
        exit 1
    fi
    
    echo "✓ 构建环境检查通过"
}

# 安装前端依赖
install_frontend_deps() {
    echo ""
    echo "安装依赖..."
    cd "$PROJECT_ROOT"
    npm install
    echo "✓ 根目录依赖安装完成"
    
    cd "$PROJECT_ROOT/frontend"
    npm install
    echo "✓ 前端依赖安装完成"
    cd "$PROJECT_ROOT"
}

# 构建 Python 后端
build_python_backend() {
    echo ""
    echo "构建 Python 后端..."
    cd "$PROJECT_ROOT/backend"
    
    # 创建虚拟环境（如果不存在）
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    pip install -r requirements.txt
    pip install pyinstaller
    
    # 使用 PyInstaller 打包
    echo "使用 PyInstaller 打包..."
    pyinstaller --clean --noconfirm localbrisk-backend.spec
    
    # 复制到 Tauri binaries 目录
    TAURI_BINARIES_DIR="$PROJECT_ROOT/src-tauri/binaries"
    mkdir -p "$TAURI_BINARIES_DIR"
    
    # 获取目标三元组
    TARGET_TRIPLE=$(rustc -vV | grep host | cut -d ' ' -f2)
    
    # 复制并重命名可执行文件
    if [ -f "dist/localbrisk-backend" ]; then
        cp "dist/localbrisk-backend" "$TAURI_BINARIES_DIR/localbrisk-backend-$TARGET_TRIPLE"
        chmod +x "$TAURI_BINARIES_DIR/localbrisk-backend-$TARGET_TRIPLE"
        echo "✓ Python 后端打包完成: localbrisk-backend-$TARGET_TRIPLE"
    else
        echo "错误: PyInstaller 打包失败"
        exit 1
    fi
    
    deactivate
}

# 生成应用图标
generate_icons() {
    echo ""
    echo "生成应用图标..."
    cd "$PROJECT_ROOT"
    
    ICONS_DIR="$PROJECT_ROOT/src-tauri/icons"
    mkdir -p "$ICONS_DIR"
    
    # 如果图标已存在则跳过
    if [ -f "$ICONS_DIR/icon.icns" ] && [ -f "$ICONS_DIR/icon.ico" ]; then
        echo "✓ 图标已存在，跳过生成"
        return
    fi
    
    # 检查是否有 logo.svg
    if [ -f "$PROJECT_ROOT/frontend/public/logo.svg" ]; then
        # 尝试使用 tauri icon 命令
        if command -v npx &> /dev/null; then
            npx tauri icon "$PROJECT_ROOT/frontend/public/logo.svg" 2>/dev/null || echo "警告: 图标生成失败，请手动创建图标"
        fi
    else
        echo "警告: 未找到 logo.svg，跳过图标生成"
    fi
}

# 构建 Tauri 应用
build_tauri_app() {
    echo ""
    echo "构建 Tauri 应用..."
    cd "$PROJECT_ROOT"
    
    npx tauri build
    
    echo "✓ Tauri 应用构建完成"
}

# 显示构建结果
show_result() {
    echo ""
    echo "======================================"
    echo "构建完成！"
    echo "======================================"
    echo ""
    echo "构建产物位置:"
    
    if [ -d "$PROJECT_ROOT/src-tauri/target/release/bundle" ]; then
        echo "  macOS: src-tauri/target/release/bundle/macos/"
        echo "  DMG:   src-tauri/target/release/bundle/dmg/"
    fi
    
    echo ""
}

# 主流程
main() {
    check_requirements
    install_frontend_deps
    build_python_backend
    generate_icons
    build_tauri_app
    show_result
}

# 运行
main "$@"
