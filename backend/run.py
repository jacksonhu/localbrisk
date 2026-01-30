#!/usr/bin/env python3
"""
LocalBrisk Backend 启动入口
用于 PyInstaller 打包的主入口文件
"""

import os
import sys

# 确保可以找到 app 模块
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    application_path = os.path.dirname(sys.executable)
else:
    # 开发环境路径
    application_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, application_path)

import uvicorn
from main import app


def main():
    """启动 FastAPI 服务"""
    # 配置参数
    host = os.environ.get("LOCALBRISK_HOST", "127.0.0.1")
    port = int(os.environ.get("LOCALBRISK_PORT", "8765"))
    
    print(f"LocalBrisk Backend 启动中...")
    print(f"服务地址: http://{host}:{port}")
    
    # 启动服务
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
