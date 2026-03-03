#!/bin/bash
# LocalBrisk 开发启动脚本
# 用于同时启动 Python 后端和 Tauri 前端

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 设置开发模式环境变量
export LOCALBRISK_DEV_MODE=1
export LOCALBRISK_DEBUG=1

echo "======================================"
echo "LocalBrisk 开发模式"
echo "======================================"
echo "日志输出: ~/Library/Logs/LocalBrisk/app.log"
echo "======================================"

# 清理函数
cleanup() {
    echo ""
    echo "正在关闭服务..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Python 虚拟环境路径
VENV_PATH="$PROJECT_ROOT/backend/venv"
PYTHON_BIN="$VENV_PATH/bin/python"
PIP_BIN="$VENV_PATH/bin/pip"

# 检查并设置虚拟环境
setup_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv "$VENV_PATH"
        echo "安装依赖包..."
        "$PIP_BIN" install -r "$PROJECT_ROOT/backend/requirements.txt"
    else
        echo "✓ 使用已存在的虚拟环境: $VENV_PATH"
        echo "  Python 版本: $($PYTHON_BIN --version)"
    fi
}

# 更新依赖包（可选）
update_deps() {
    echo "检查并更新依赖包..."
    "$PIP_BIN" install -r "$PROJECT_ROOT/backend/requirements.txt" --quiet --upgrade
}

# 启动 Python 后端
start_backend() {
    echo "启动 Python 后端..."
    cd "$PROJECT_ROOT/backend"
    
    # 设置虚拟环境
    setup_venv
    
    # 如果传入了 --update-deps 参数，则更新依赖
    if [ "$UPDATE_DEPS" = "1" ]; then
        update_deps
    fi
    
    # 后台启动 Python 服务（直接使用 venv 中的 python，无需 activate）
    "$PYTHON_BIN" main.py &
    BACKEND_PID=$!
    echo "✓ Python 后端已启动 (PID: $BACKEND_PID)"
    
    # 等待服务启动
    echo "等待后端服务就绪..."
    sleep 2
    
    # 检查服务是否启动成功
    if curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
        echo "✓ 后端服务就绪: http://127.0.0.1:8765"
    else
        echo "警告: 后端服务可能未完全启动，请检查日志"
    fi
    
    cd "$PROJECT_ROOT"
}

# 启动 Tauri 开发服务
start_tauri() {
    echo ""
    echo "启动 Tauri 开发服务..."
    
    # 安装根目录依赖（如果需要）
    cd "$PROJECT_ROOT"
    if [ ! -d "node_modules" ]; then
        echo "安装根目录依赖..."
        npm install
    fi
    
    # 安装前端依赖（如果需要）
    cd "$PROJECT_ROOT/frontend"
    if [ ! -d "node_modules" ]; then
        echo "安装前端依赖..."
        npm install
    fi
    
    # 回到项目根目录运行 Tauri（因为 src-tauri 在根目录下）
    cd "$PROJECT_ROOT"
    
    # 启动 Tauri 开发模式
    npx tauri dev
}

# 显示帮助信息
show_help() {
    echo "用法: ./dev.sh [选项]"
    echo ""
    echo "选项:"
    echo "  --update-deps    启动前更新 Python 依赖包"
    echo "  --backend-only   只启动后端服务"
    echo "  --frontend-only  只启动前端服务"
    echo "  --help           显示帮助信息"
    echo ""
}

# 主流程
main() {
    UPDATE_DEPS=0
    BACKEND_ONLY=0
    FRONTEND_ONLY=0
    
    # 解析命令行参数
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --update-deps)
                UPDATE_DEPS=1
                shift
                ;;
            --backend-only)
                BACKEND_ONLY=1
                shift
                ;;
            --frontend-only)
                FRONTEND_ONLY=1
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [ "$FRONTEND_ONLY" = "1" ]; then
        start_tauri
    elif [ "$BACKEND_ONLY" = "1" ]; then
        start_backend
        echo ""
        echo "按 Ctrl+C 停止服务..."
        wait $BACKEND_PID
    else
        start_backend
        start_tauri
    fi
}

main "$@"
