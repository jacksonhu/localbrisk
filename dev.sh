#!/bin/bash
# LocalBrisk 开发启动脚本
# 用于同时启动 Python 后端和 Tauri 前端

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "======================================"
echo "LocalBrisk 开发模式"
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

# 启动 Python 后端
start_backend() {
    echo "启动 Python 后端..."
    cd "$PROJECT_ROOT/backend"
    
    # 创建虚拟环境（如果不存在）
    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # 后台启动 Python 服务
    python main.py &
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

# 主流程
main() {
    start_backend
    start_tauri
}

main "$@"
